# analysis/lexical/analyze_lexical.py
# Run from repo root: python analysis/lexical/analyze_lexical.py
# No network, no subprocess, no eval, no installs. Writes only under analysis/lexical/.

import json
import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

SEED = 20261104
ALPHAS = [0.1, 1.0, 10.0, 100.0, 1000.0]
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "analysis/lexical"
OUT.mkdir(parents=True, exist_ok=True)

RAW = ROOT / Path("data/raw/komura2026/s003.xlsx")
PART = ROOT / Path("results/cocreation_participants.csv")
PRED_P = ROOT / Path("results/cocreation_predictions_participant.csv")
PRED_C = ROOT / Path("results/cocreation_predictions_condition.csv")



def fail(msg):
    print("FATAL:", msg, file=sys.stderr)
    sys.exit(1)


def load_notes():
    df = pd.read_excel(RAW, sheet_name="notes_detailed")
    need = {"sessionId", "creator", "content", "turnId"}
    if not need.issubset(df.columns):
        fail(f"notes_detailed missing columns: {need - set(df.columns)}")
    df = df[df["creator"].astype(str).str.lower() == "ai"].copy()
    df["content"] = df["content"].fillna("").astype(str)
    # aggregate AI ideas per session, ordered by turnId for determinism
    df = df.sort_values(["sessionId", "turnId"])
    agg = df.groupby("sessionId", sort=False)["content"].apply(lambda s: " ".join(s)).reset_index()
    agg.columns = ["sessionId", "ai_text"]
    return agg


def build_design(part):
    p = part.copy()
    # keep known aitype only (142)
    if p["sessionId"].duplicated().any():
        fail("duplicate source participant IDs")
    p = p[p["aitype"].isin(["vertical", "horizontal", "random"])].copy()
    p["aitype"] = p["aitype"].astype(str)
    # numeric design/user/logs
    for c in ["age", "log_duration", "user_notes", "log_ai_chars", "log_user_chars",
              "max_grid_row", "max_grid_col"]:
        if c in p.columns:
            p[c] = pd.to_numeric(p[c], errors="coerce")
    keep = ["sessionId", "aitype", "gender", "intelligence",
            "age", "log_duration", "user_notes", "log_ai_chars", "log_user_chars",
            "max_grid_row", "max_grid_col"]
    if not set(keep).issubset(p.columns):
        fail("missing required baseline columns")
    return p[keep]


def load_folds(path, name):
    f = pd.read_csv(path)
    if "sessionId" not in f.columns or "fold" not in f.columns:
        fail(f"{name}: need sessionId, fold")
    if f["sessionId"].duplicated().any() or f[["sessionId","fold"]].isna().any().any():
        fail("duplicate or missing outer fold entries")
    return f[["sessionId", "fold"]]


def make_pipeline(num_cols, cat_cols, text_col, with_text):
    num_pipe = Pipeline([
        ("imp", SimpleImputer(strategy="median")),
        ("sc", StandardScaler()),
    ])
    cat_pipe = Pipeline([
        ("imp", SimpleImputer(strategy="most_frequent")),
        ("oh", OneHotEncoder(handle_unknown="ignore")),
    ])
    transformers = []
    if num_cols:
        transformers.append(("num", num_pipe, num_cols))
    if cat_cols:
        transformers.append(("cat", cat_pipe, cat_cols))
    if with_text:
        transformers.append(("txt", TfidfVectorizer(
            analyzer="char", ngram_range=(3, 5), min_df=2, max_features=10000), text_col))
    ct = ColumnTransformer(transformers, remainder="drop", sparse_threshold=0.3)
    return Pipeline([("ct", ct), ("ridge", Ridge(solver="lsqr"))])


def run_outer(design, folds, name, text_col, with_text, feat_cols_num, feat_cols_cat):
    # outer folds from file
    outer_ids = sorted(folds["sessionId"].astype(str).unique())
    design = design.copy()
    design["sessionId"] = design["sessionId"].astype(str)
    design = design.set_index("sessionId")
    if not set(outer_ids).issubset(set(design.index)):
        fail(f"{name}: fold IDs not subset of design IDs")
    # one-to-one check
    if design.index.duplicated().any():
        fail(f"{name}: duplicate sessionId in design")

    oof = pd.Series(index=design.index, dtype=float, name=f"pred_{name}")
    chosen = []
    for fold_val in sorted(folds["fold"].unique()):
        test_ids = folds.loc[folds["fold"] == fold_val, "sessionId"].astype(str).tolist()
        train_ids = [i for i in design.index if i not in set(test_ids)]
        if set(train_ids) & set(test_ids):
            fail(f"{name}: train/test overlap")
        Xtr = design.loc[train_ids, feat_cols_num + feat_cols_cat + ([text_col] if with_text else [])]
        Xte = design.loc[test_ids, feat_cols_num + feat_cols_cat + ([text_col] if with_text else [])]
        ytr = design.loc[train_ids, "intelligence"].to_numpy(dtype=float)
        # inner KFold for alpha
        inner = KFold(n_splits=4, shuffle=True, random_state=SEED + int(fold_val))
        best_alpha, best_mse = None, np.inf
        for a in ALPHAS:
            inner_mse = []
            for tr_i, va_i in inner.split(Xtr):
                pipe = make_pipeline(feat_cols_num, feat_cols_cat, text_col, with_text)
                pipe.set_params(ridge__alpha=a)
                pipe.fit(Xtr.iloc[tr_i], ytr[tr_i])
                pred = pipe.predict(Xtr.iloc[va_i])
                inner_mse.append(mean_squared_error(ytr[va_i], pred))
            mse = float(np.mean(inner_mse))
            if mse < best_mse:
                best_mse, best_alpha = mse, a
        pipe = make_pipeline(feat_cols_num, feat_cols_cat, text_col, with_text)
        pipe.set_params(ridge__alpha=best_alpha)
        pipe.fit(Xtr, ytr)
        pred = pipe.predict(Xte)
        if not np.all(np.isfinite(pred)):
            fail(f"{name}: non-finite predictions")
        oof.loc[test_ids] = pred
        chosen.append({"outer_fold": int(fold_val), "alpha": best_alpha, "n_train": len(train_ids), "n_test": len(test_ids)})
    if oof.isna().any():
        fail(f"{name}: missing OOF predictions")
    return oof, chosen


def metrics(y_true, y_pred):
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
        "n": int(len(y_true)),
    }


def main():
    if not RAW.exists() or not PART.exists() or not PRED_P.exists() or not PRED_C.exists():
        fail("missing required input file(s)")

    notes = load_notes()
    part = build_design(pd.read_csv(PART))

    # keep 142 known aitype; one-to-one merge with AI text
    if part["sessionId"].duplicated().any():
        fail("participants: duplicated sessionId")
    merged = part.merge(notes, on="sessionId", how="inner", validate="one_to_one")
    if len(merged) != 142:
        fail(f"expected 142 known-aitype rows after merge, got {len(merged)}")

    # Only the original content column is concatenated. Metadata/outcome fields
    # are never serialized into text; legitimate lexical matches are not deleted.

    y = merged["intelligence"].to_numpy(dtype=float)
    if not np.all(np.isfinite(y)):
        fail("non-finite intelligence outcome")

    num_cols = [c for c in ["age", "log_duration", "user_notes", "log_ai_chars",
                             "log_user_chars", "max_grid_row", "max_grid_col"] if c in merged.columns]
    cat_cols = [c for c in ["aitype", "gender"] if c in merged.columns]
    text_col = "ai_text"

    folds_p = load_folds(PRED_P, "participant")
    folds_c = load_folds(PRED_C, "condition")

    schemes = {"participant": folds_p, "condition": folds_c}
    results = {}
    all_preds = merged[["sessionId"]].copy()

    for sname, folds in schemes.items():
        ids_f = set(folds["sessionId"].astype(str))
        ids_d = set(merged["sessionId"].astype(str))
        if ids_f != ids_d:
            fail(f"{sname}: fold IDs != known 142 IDs")
        # baseline: train mean
        base = pd.Series(index=merged["sessionId"].astype(str), dtype=float)
        for fv in sorted(folds["fold"].unique()):
            te = folds.loc[folds["fold"] == fv, "sessionId"].astype(str).tolist()
            tr = [i for i in base.index if i not in set(te)]
            base.loc[te] = float(np.mean(merged.set_index("sessionId").loc[tr, "intelligence"]))
        if base.isna().any():
            fail(f"{sname}: missing train-mean predictions")

        mdl = merged.set_index("sessionId")
        y_m = mdl.loc[base.index, "intelligence"].to_numpy(dtype=float)

        p_design, a_design = run_outer(
            mdl.reset_index(), folds, f"{sname}_design", text_col, False, num_cols, cat_cols)
        p_text, a_text = run_outer(
            mdl.reset_index(), folds, f"{sname}_text", text_col, True, num_cols, cat_cols)

        # reindex to same order
        idx = base.index
        p_design = p_design.reindex(idx)
        p_text = p_text.reindex(idx)
        if p_design.isna().any() or p_text.isna().any():
            fail(f"{sname}: prediction misalignment")

        m_base = metrics(y_m, base.to_numpy())
        m_des = metrics(y_m, p_design.to_numpy())
        m_txt = metrics(y_m, p_text.to_numpy())
        d_text = {k: m_txt[k] - m_des[k] for k in ["MAE", "RMSE", "R2"]}

        results[sname] = {
            "train_mean": m_base,
            "design_user_logs": m_des,
            "design_user_logs_ai_text": m_txt,
            "delta_text_vs_design": d_text,
            "chosen_alphas_design": a_design,
            "chosen_alphas_text": a_text,
        }
        all_preds[f"{sname}_train_mean"] = base.reindex(idx).to_numpy()
        all_preds[f"{sname}_design"] = p_design.to_numpy()
        all_preds[f"{sname}_text"] = p_text.to_numpy()

    # checks
    if all_preds["sessionId"].duplicated().any():
        fail("duplicated sessionId in predictions output")
    pred_cols = [c for c in all_preds.columns if c != "sessionId"]
    if not np.all(np.isfinite(all_preds[pred_cols].to_numpy(dtype=float))):
        fail("non-finite prediction in output table")

    all_preds.to_csv(OUT / "lexical_oof_predictions.csv", index=False)
    with open(OUT / "lexical_metrics.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    manifest = {
        "input_sha256": {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [RAW,PART,PRED_P,PRED_C]},
        "seed": SEED, "alphas": ALPHAS, "n_known_aitype": int(len(merged)),
        "n_notes_ai_sessions": int(len(notes)),
        "outer_schemes": list(schemes.keys()),
        "text_vectorizer": "TF-IDF char (3,5), min_df=2, max_features=10000",
        "estimator": "Ridge(solver=lsqr)",
        "inner_folds": 4,
        "note": "lexical content feature; not objective quality; no CIs/p-values generated",
    }
    with open(OUT / "lexical_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print("DONE. Wrote analysis/lexical/lexical_oof_predictions.csv, lexical_metrics.json, lexical_manifest.json")


if __name__ == "__main__":
    main()