"""Authored fictional stimuli, not conversations or observations from a model."""
VERSION = 'process-transfer-0.1'
ARMS = ('derived', 'supplied')
CELLS = ('same_same', 'same_different', 'different_same', 'different_different')
RATINGS = {
    'smartness': 'Ассистент в этом сценарии показался мне умным.',
    'liking': 'Ассистент в этом сценарии мне понравился.',
    'usefulness': 'Конечный результат в этом сценарии был полезен для поставленной задачи.',
    'reading_effort': 'Мне потребовалось много усилий, чтобы разобраться в сценарии.',
}
# A balanced Latin square: each cell occupies each position and precedes each other once.
ORDERS = ((0, 1, 3, 2), (1, 2, 0, 3), (2, 3, 1, 0), (3, 0, 2, 1))


def clock(minutes):
    return f'{minutes // 60:02d}:{minutes % 60:02d}'


def dependency(topic, variant, exposure=False):
    if topic == 'schedule':
        start, old, new, following = 540 + variant * 60, 20, 35, 25
        request = (f'Занятие начинается в {clock(start)}. Первый блок длится {old} минут, '
                   f'сразу за ним второй — {following} минут. Первый блок теперь длится {new} минут. '
                   'Обновите время начала и конца второго блока. Комната остаётся № 7.')
        patch = f'Начало второго блока {clock(start + new)}, конец {clock(start + new + following)}.'
        rule = f'{clock(start)} + {new} мин = {clock(start + new)}; ещё {following} мин = {clock(start + new + following)}.'
        final = patch + ' Комната № 7.'
        truth = {'start': start, 'new_duration': new, 'following': following,
                 'second_start': start + new, 'second_end': start + new + following}
    else:
        opening, old, new, dispatch = 80 + variant * 20, 20, 35, 25
        request = (f'На складе {opening} коробок. Ожидали поступление {old} коробок, '
                   f'затем отправку {dispatch}. Поступление изменилось на {new}. '
                   'Обновите запас после поступления и после отправки. Место хранения остаётся А7.')
        patch = f'После поступления {opening + new} коробок, после отправки {opening + new - dispatch}.'
        rule = f'{opening} + {new} = {opening + new}; {opening + new} − {dispatch} = {opening + new - dispatch}.'
        final = patch + ' Место А7.'
        truth = {'opening': opening, 'new_delivery': new, 'dispatch': dispatch,
                 'after_delivery': opening + new, 'after_dispatch': opening + new - dispatch}
    return dict(request=request, patch=patch, rule=rule, final=final, truth=truth)


def selection(topic, variant):
    # A deliberately different operation: apply a constraint then select the minimum.
    # Cognitive difficulty/equivalence must be assessed by humans, not assumed here.
    threshold = 12 + variant * 2
    if topic == 'schedule':
        request = (f'Выберите самый дешёвый зал вместимостью не меньше {threshold} человек. '
                   f'Зал А: {threshold - 2} мест, 400 ₽; Б: {threshold} мест, 700 ₽; '
                   f'В: {threshold + 4} мест, 900 ₽. Назовите зал и цену.')
    else:
        request = (f'Выберите самую дешёвую упаковку вместимостью не меньше {threshold} предметов. '
                   f'Упаковка А: {threshold - 2} мест, 400 ₽; Б: {threshold} мест, 700 ₽; '
                   f'В: {threshold + 4} мест, 900 ₽. Назовите упаковку и цену.')
    return dict(request=request, final='Б, 700 ₽.',
                truth={'threshold': threshold, 'capacities': [threshold-2, threshold, threshold+4],
                       'prices': [400, 700, 900], 'selected_index': 1})


def material(topic, variant, arm):
    if topic not in ('schedule', 'inventory') or variant not in (0, 1) or arm not in ARMS:
        raise ValueError('Unknown authored stimulus')
    exposed = dependency(topic, variant, True)
    source = ('Ассистент сам вычислил поправку по исходным данным: ' if arm == 'derived' else
              'Отдельный вычислительный модуль сам вычислил поправку и передал её ассистенту: ')
    # The same arithmetic information and the same final artifact in both arms.
    process = source + exposed['rule'] + ' Ассистент внёс поправку в результат.'
    probes = []
    for cell in CELLS:
        same_topic, same_operation = cell.split('_')
        target_topic = topic if same_topic == 'same' else ('inventory' if topic == 'schedule' else 'schedule')
        item = (dependency if same_operation == 'same' else selection)(target_topic, variant + 3)
        probes.append(dict(id=cell, topic=target_topic,
                           operation='dependency' if same_operation == 'same' else 'selection', **item))
    return dict(exposure_id=f'{topic}-{variant}', topic=topic, variant=variant, arm=arm,
                request=exposed['request'], process=process, final=exposed['final'],
                truth=exposed['truth'], probes=probes)
