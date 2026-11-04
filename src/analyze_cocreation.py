"""Reproducible exploratory analysis of Komura & Yamada (2026) open data.

No API model calls, synthetic participants, or generated ratings. Read-only raw
workbook, explicit keyed joins, participant-disjoint nested prediction.
"""
from pathlib import Path
import os
import json
import warnings

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.mplconfig'))
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import StratifiedKFold, KFold, GridSearchCV
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from semopy import Model, calc_stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SEED = 20261104
OUT = ROOT / 'results'
FIG = OUT / 'figures'


def alpha(x):
    a = np.asarray(x, dtype=float)
    k = a.shape[1]
    return float(k / (k - 1) * (1 - a.var(axis=0, ddof=1).sum() / a.sum(axis=1).var(ddof=1)))


def htmt(a, b, rank=False):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if rank:
        a, b = stats.rankdata(a, axis=0), stats.rankdata(b, axis=0)
    k, m = a.shape[1], b.shape[1]
    c = np.abs(np.corrcoef(np.column_stack([a, b]), rowvar=False))
    wa = c[:k, :k][np.triu_indices(k, 1)].mean()
    wb = c[k:, k:][np.triu_indices(m, 1)].mean()
    return float(c[:k, k:].mean() / np.sqrt(wa * wb))


def load_data():
    book = ROOT / 'data/raw/komura2026/s003.xlsx'
    q = pd.read_excel(book, sheet_name='questionnaires')
    m = pd.read_excel(book, sheet_name='sessions_metrics')
    notes = pd.read_excel(book, sheet_name='notes_detailed')
    assert len(q) == 148 and q.sessionId.is_unique and m.sessionId.is_unique
    assert set(q.sessionId) == set(m.sessionId) == set(notes.sessionId)
    # Three-digit anonymized note IDs collide even within sessions. The release's
    # session/creator/turn tuple is unique and is the appropriate observation key.
    assert not notes.duplicated(['sessionId','creator','turnId']).any()
    d = q.merge(m, on=['sessionId', 'aitype'], validate='one_to_one')
    assert len(d) == len(q)
    assert (d.selected_notes_count == d.selected_ai_notes_count + d.selected_user_notes_count).all()
    item_sets = {
        'intelligence': [f'gqs_perceived_intelligence_{i}' for i in range(1, 6)],
        'capable': [f'mdmt_capable_{i}' for i in range(1, 5)],
        'reliable': [f'mdmt_reliable_{i}' for i in range(1, 5)],
        'likeability': [f'gqs_likeability_{i}' for i in range(1, 6)],
    }
    for name, cols in item_sets.items():
        assert not d[cols].isna().any().any()
        lo, hi = (1, 5) if name in ['intelligence', 'likeability'] else (0, 7)
        assert d[cols].ge(lo).all().all() and d[cols].le(hi).all().all()
        d[name] = d[cols].mean(axis=1)
    notes['chars'] = notes.content.astype(str).str.len()
    counts = notes.groupby(['sessionId', 'creator']).size().unstack()
    lengths = notes.groupby(['sessionId', 'creator'])['chars'].mean().unstack()
    chosen = notes.groupby(['sessionId', 'creator'])['is_selected'].sum().unstack()
    for role in ['ai', 'user']:
        d[f'{role}_notes'] = d.sessionId.map(counts[role])
        d[f'{role}_chars_mean'] = d.sessionId.map(lengths[role])
    # Independently reconcile detailed logs against the published session metrics.
    discrepancies = []
    for role in ['ai', 'user']:
        expected = d.sessionId.map(chosen[role]).astype(int)
        col = f'selected_{role}_notes_count'
        for i in np.where(expected.to_numpy() != d[col].to_numpy())[0]:
            discrepancies.append({'sessionId': d.iloc[i].sessionId, 'field': col,
                                  'summary': int(d.iloc[i][col]), 'detail': int(expected.iloc[i])})
    d['adoption_fraction'] = d.selected_ai_notes_count / d.ai_notes
    d['log_duration'] = np.log1p(d.session_duration_seconds)
    d['log_ai_chars'] = np.log1p(d.ai_chars_mean)
    d['log_user_chars'] = np.log1p(d.user_chars_mean)
    d = d.rename(columns={'participantInfo_age': 'age', 'participantInfo_gender': 'gender'})
    assert d[['adoption_fraction','log_duration','log_ai_chars','log_user_chars']].notna().all().all()
    audit = {'n': len(d), 'raw_note_rows': len(notes), 'raw_note_sessions': notes.sessionId.nunique(),
             'conditions': d.aitype.value_counts().to_dict(), 'missing_analyzed_values': 0,
             'selection_summary_detail_discrepancies': discrepancies,
             'paper_note_count': 5848, 'observed_note_count': len(notes),
             'duplicate_anonymized_note_ids': int(notes.note_id.duplicated().sum()),
             'duplicate_note_ids_within_session': int(notes.duplicated(['sessionId','note_id']).sum()),
             'unknown_condition_sessions': d.loc[d.aitype=='unknown','sessionId'].tolist(),
             'instrument_warning': 'Adapted Godspeed includes responsiveness; likeability duplicates unpleasant/pleasant. No cross-study scale equivalence assumed.'}
    return d, item_sets, audit


def measurement(d, sets):
    out = {'alpha': {k: alpha(d[v]) for k, v in sets.items()}, 'htmt': []}
    rng = np.random.default_rng(SEED)
    for name in ['capable', 'reliable', 'likeability']:
        a, b = d[sets['intelligence']].to_numpy(), d[sets[name]].to_numpy()
        boot = []
        for _ in range(2000):
            ids = rng.integers(0, len(d), len(d))
            boot.append(htmt(a[ids], b[ids]))
        out['htmt'].append({'pair': f'intelligence_{name}', 'estimate': htmt(a, b),
                            'ci_low': float(np.quantile(boot, .025)), 'ci_high': float(np.quantile(boot, .975)),
                            'rank_htmt': htmt(a, b, rank=True)})
    cols = sets['intelligence'] + sets['capable'] + sets['reliable']
    renamed = {c: f'x{i+1}' for i, c in enumerate(cols)}
    x = d[cols].rename(columns=renamed)
    models = {
        'one_factor': 'G =~ ' + ' + '.join(x.columns),
        'two_factors': 'I =~ ' + ' + '.join(x.columns[:5]) + '\nT =~ ' + ' + '.join(x.columns[5:]),
        'three_factors': 'I =~ ' + ' + '.join(x.columns[:5]) + '\nC =~ ' + ' + '.join(x.columns[5:9]) + '\nR =~ ' + ' + '.join(x.columns[9:]),
    }
    fits = []
    for name, syntax in models.items():
        model = Model(syntax)
        fitted = model.fit(x, obj='MLW')
        stat = calc_stats(model).iloc[0].to_dict()
        # semopy's default AIC/BIC use its discrepancy scale. Supply comparable
        # likelihood criteria relative to the same saturated model instead.
        k = sum(p.active for p in model.parameters.values())
        stat.pop('AIC',None); stat.pop('BIC',None); stat.pop('LogLik',None)
        stat['AIC_relative_saturated'] = stat['chi2'] + 2*k
        stat['BIC_relative_saturated'] = stat['chi2'] + np.log(len(d))*k
        table = model.inspect(std_est=True)
        table.to_csv(OUT / f'cocreation_cfa_{name}_parameters.csv', index=False)
        fits.append({'model': name, 'success': bool(fitted.success), **{k: float(v) for k,v in stat.items()}})
    out['cfa'] = fits
    out['cfa_note'] = 'Continuous-item ML covariance models; no robust ordinal chi-square. Treat fit indices as exploratory, not definitive factor validation.'
    return out


def pipeline(cols, nonlinear=False):
    categorical = [c for c in cols if c in ['aitype', 'gender']]
    numeric = [c for c in cols if c not in categorical]
    prep = ColumnTransformer([
        ('numeric', Pipeline([('impute', SimpleImputer(strategy='median')), ('scale', StandardScaler())]), numeric),
        ('categorical', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical),
    ])
    estimator = HistGradientBoostingRegressor(max_iter=100,min_samples_leaf=15,early_stopping=False,random_state=SEED) if nonlinear else Ridge()
    return Pipeline([('preprocess', prep), ('estimator', estimator)])


def run_prediction(d, blocks, split_mode='participant', seed=SEED):
    y = d.intelligence.to_numpy()
    if split_mode == 'participant':
        splits = list(StratifiedKFold(5, shuffle=True, random_state=seed).split(d, d.aitype))
    else:
        splits = [(np.flatnonzero((d.aitype != c).to_numpy()), np.flatnonzero((d.aitype == c).to_numpy())) for c in sorted(d.aitype.unique())]
    rows, pred, tuning = [], pd.DataFrame({'sessionId': d.sessionId, 'aitype': d.aitype, 'observed': y}), []
    pred['fold'] = -1
    for name, cols in {'training_mean': [], **blocks}.items():
        p = np.empty(len(d))
        for fold, (tr, te) in enumerate(splits):
            assert not set(tr) & set(te)
            pred.loc[te, 'fold'] = fold
            if not cols:
                p[te] = y[tr].mean()
                continue
            inner = KFold(4, shuffle=True, random_state=seed+fold)
            nonlinear = name.startswith('nonlinear_')
            grid = {'estimator__max_leaf_nodes':[3,7], 'estimator__l2_regularization':[1.,10.]} if nonlinear else {'estimator__alpha': [.1, 1., 10., 100.]}
            fit = GridSearchCV(pipeline(cols, nonlinear), grid, cv=inner,
                               scoring='neg_mean_squared_error', n_jobs=1)
            fit.fit(d.iloc[tr][cols], y[tr])
            p[te] = fit.predict(d.iloc[te][cols])
            tuning.append({'split': split_mode, 'fold': fold, 'model': name, 'parameters': json.dumps(fit.best_params_)})
        pred[name] = p
        rows.append({'split': split_mode, 'model': name, 'n': len(y), 'rmse': float(np.sqrt(mean_squared_error(y,p))),
                     'mae': float(mean_absolute_error(y,p)), 'r2': float(r2_score(y,p))})
    rng = np.random.default_rng(SEED + 7)
    for row in rows:
        name = row['model']; p = pred[name].to_numpy(); base = pred.training_mean.to_numpy()
        r2s, deltas = [], []
        for _ in range(2000):
            ix = rng.integers(0, len(y), len(y))
            r2s.append(r2_score(y[ix], p[ix]))
            deltas.append(np.sqrt(mean_squared_error(y[ix], p[ix])) - np.sqrt(mean_squared_error(y[ix], base[ix])))
        row.update(r2_low=float(np.quantile(r2s,.025)), r2_high=float(np.quantile(r2s,.975)),
                   delta_rmse=row['rmse']-rows[0]['rmse'], delta_rmse_low=float(np.quantile(deltas,.025)),
                   delta_rmse_high=float(np.quantile(deltas,.975)))
    return rows, pred, tuning


def regressions(d):
    rows=[]
    formulas = {
        'design_only': 'intelligence ~ C(aitype) + age + C(gender)',
        'telemetry': 'intelligence ~ C(aitype) + age + C(gender) + log_duration + user_notes + log_ai_chars + log_user_chars',
        'behavior': 'intelligence ~ C(aitype) + age + C(gender) + log_duration + user_notes + log_ai_chars + log_user_chars + adoption_fraction',
        'same_survey': 'intelligence ~ C(aitype) + age + C(gender) + capable + reliable',
    }
    for name, f in formulas.items():
        model=smf.ols(f, d).fit(cov_type='HC3')
        assert np.linalg.matrix_rank(model.model.exog) == model.model.exog.shape[1]
        ci=model.conf_int()
        for term in model.params.index:
            rows.append({'model': name,'term':term,'coefficient':float(model.params[term]), 'ci_low':float(ci.loc[term,0]),
                         'ci_high':float(ci.loc[term,1]),'p_two_sided':float(model.pvalues[term]),'n':int(model.nobs),'r2_in_sample':model.rsquared})
    table=pd.DataFrame(rows)
    # Each formula is an exploratory family of all non-intercept coefficient tests.
    table['p_holm_within_model']=np.nan
    for name in table.model.unique():
        mask=(table.model==name)&(table.term!='Intercept')
        table.loc[mask,'p_holm_within_model']=multipletests(table.loc[mask,'p_two_sided'],method='holm')[1]
    return table


def main():
    OUT.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True,parents=True)
    d, sets, audit = load_data()
    print('Data audit:', json.dumps(audit), flush=True)
    # Never export free-text comments/ideas or identifiers beyond source-anonymized session IDs.
    d.drop(columns=['aiFeedback_comment'],errors='ignore').to_csv(OUT/'cocreation_participants.csv',index=False)
    measure = measurement(d, sets)
    base = ['aitype','age','gender']
    logs = base + ['log_duration','user_notes','log_ai_chars','log_user_chars','max_grid_row','max_grid_col']
    blocks = {'design_user':base, 'telemetry':logs, 'telemetry_adoption':logs+['adoption_fraction'],
              'same_survey_benchmark':base+['capable','reliable'],
              'nonlinear_telemetry':logs, 'nonlinear_telemetry_adoption':logs+['adoption_fraction'],
              'nonlinear_same_survey':base+['capable','reliable']}
    # Six source records have unknown assignment. Keep them in measurement,
    # exclude from condition-based primary prediction, preserve in sensitivity.
    known = d[d.aitype!='unknown'].reset_index(drop=True)
    rows, predictions, tunes = run_prediction(known, blocks)
    predictions.to_csv(OUT/'cocreation_predictions_participant.csv',index=False)
    loo, predictions, t = run_prediction(known, blocks, 'condition')
    predictions.to_csv(OUT/'cocreation_predictions_condition.csv',index=False)
    pd.DataFrame(rows+loo).to_csv(OUT/'cocreation_prediction_metrics.csv',index=False)
    pd.DataFrame(tunes+t).to_csv(OUT/'cocreation_tuning.csv',index=False)
    sensitivity, _, _ = run_prediction(d, blocks)
    pd.DataFrame(sensitivity).to_csv(OUT/'cocreation_prediction_unknown_included.csv',index=False)
    regression = regressions(known); regression.to_csv(OUT/'cocreation_regressions.csv',index=False)
    # Continuous composite vs direct integer intelligence item: rank robustness without discretization.
    corr=[]
    for outcome in ['intelligence','gqs_perceived_intelligence_5']:
        for predictor in ['capable','reliable','adoption_fraction','log_duration','log_ai_chars','log_user_chars']:
            rho,p=stats.spearmanr(d[outcome],d[predictor])
            corr.append({'outcome':outcome,'predictor':predictor,'spearman_rho':float(rho),'p_two_sided':float(p)})
    c=pd.DataFrame(corr);c['p_holm']=multipletests(c.p_two_sided,method='holm')[1];c.to_csv(OUT/'cocreation_rank_sensitivity.csv',index=False)
    summary={'audit':audit,'measurement':measure,'prediction_features':blocks,
             'descriptives':d.groupby('aitype')[['intelligence','capable','reliable','adoption_fraction']].agg(['mean','std','count']).to_json(),
             'uncertainty':'2000 participant resamples of fixed OOF predictions, conditional on training; not full training uncertainty.',
             'source':'https://doi.org/10.1371/journal.pone.0340449'}
    (OUT/'cocreation_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    fig,ax=plt.subplots(figsize=(8.4,4.6),layout='constrained')
    names=['design_user','telemetry','telemetry_adoption','same_survey_benchmark']; labels=['Design + user','+ interaction logs','+ end-session adoption','Same-survey trust']
    for j,(split,rr,col) in enumerate([('Participant CV',rows,'#21618c'),('Held-out condition',loo,'#c16732')]):
        rr={r['model']:r for r in rr}; yy=np.arange(len(names))+(j-.5)*.22
        vals=np.array([rr[n]['r2'] for n in names]); low=np.array([rr[n]['r2_low'] for n in names]);high=np.array([rr[n]['r2_high'] for n in names])
        ax.errorbar(vals,yy,xerr=[vals-low,high-vals],fmt='o',label=split,color=col,capsize=3)
    ax.axvline(0,color='#555555',linewidth=1);ax.set_yticks(np.arange(len(names)),labels);ax.invert_yaxis()
    ax.set_xlabel('Out-of-sample R² (95% conditional bootstrap interval)')
    ax.set_title('Text co-creation: predicting perceived intelligence, n=142')
    ax.legend(frameon=False,loc='lower right');fig.savefig(FIG/'cocreation_prediction.png',dpi=180);plt.close(fig)
    print(pd.DataFrame(rows+loo).to_string(index=False),flush=True)
    print('Saved co-creation outputs.',flush=True)


if __name__=='__main__':
    main()
