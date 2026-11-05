"""Authored paired-operation stimuli. No real model traces or human observations."""
VERSION='process-transfer-0.2'
OPERATIONS=('dependency','selection')
ARMS=('assistant_dependency','assistant_selection')
TOOLS=('unavailable','available')
CELLS=('same_same','same_different','different_same','different_different')
ABS_CELLS=('same_dependency','same_selection','different_dependency','different_selection')
RATINGS={
 'smartness':'Ассистент в этом сценарии показался мне умным.',
 'liking':'Ассистент в этом сценарии мне понравился.',
 'usefulness':'Конечный результат был полезен для поставленной задачи.',
 'reading_effort':'Мне потребовалось много усилий, чтобы разобраться в сценарии.',
 'credit':'Большая часть итогового результата — заслуга ассистента.',
}
CHECKS=('dependency_source','selection_source','tools','allocation','clarity','interpretation')
ORDERS=((0,1,3,2),(1,2,0,3),(2,3,1,0),(3,0,2,1))
PROCESS_ORDERS=('dependency_first','selection_first')
RESOURCE_SCOPE=('Отдельный модуль принимает задачи обоих показанных типов. Частота ошибок '
                'ассистента и модуля неизвестна; доступ к модулю не гарантирует правильный ответ.')
DISPATCH=('В этом вымышленном эпизоде организатор случайно назначил исполнителя каждого этапа, независимо от способностей; '
          'ассистент не выбирал, что делегировать. Каждый исполнитель выполнил один этап. '
          'Из этой записи не следует, что он не способен выполнить другой тип задачи.')
LABELS={'dependency':'Часть А','selection':'Часть Б'}


def clock(minutes):return f'{minutes//60:02d}:{minutes%60:02d}'


def dependency(topic,variant,exposure=False):
    if topic not in ('schedule','inventory') or variant not in (0,1):raise ValueError('Unknown dependency stimulus')
    shift=0 if exposure else 30
    if topic=='schedule' and variant==0:
        start,old,new,following=540+shift,20,35,25
        request=(f'Занятие начинается в {clock(start)}. Первый блок длится {old} минут, сразу за ним второй — '
                 f'{following} минут. Первый блок теперь длится {new} минут. Обновите начало и конец второго блока. '
                 'Название занятия остаётся «Практикум».')
        rule=f'{clock(start)} + {new} мин = {clock(start+new)}; ещё {following} мин = {clock(start+new+following)}.'
        final=f'Второй блок: {clock(start+new)}–{clock(start+new+following)}. Название: «Практикум».'
        truth=dict(direction='forward',inputs=[start,new,following],outputs=[start+new,start+new+following])
    elif topic=='schedule':
        end,old,new,following=660+shift,20,35,25
        request=(f'Второй блок должен закончиться в {clock(end)} и длится {following} минут. '
                 f'Перед ним без перерыва идёт первый блок: вместо {old} он теперь длится {new} минут. '
                 'Обновите начало первого и второго блоков. Название занятия остаётся «Практикум».')
        rule=f'{clock(end)} − {following} мин = {clock(end-following)}; ещё − {new} мин = {clock(end-following-new)}.'
        final=f'Первый блок начинается {clock(end-following-new)}, второй {clock(end-following)}. Название: «Практикум».'
        truth=dict(direction='backward',inputs=[end,new,following],outputs=[end-following-new,end-following])
    elif variant==0:
        opening,old,new,dispatch=80+shift,20,35,25
        request=(f'На складе {opening} коробок. Ожидали поступление {old}, затем отправку {dispatch}. '
                 f'Поступление изменилось на {new}. Обновите запас после поступления и после отправки. Место хранения — А7.')
        rule=f'{opening} + {new} = {opening+new}; {opening+new} − {dispatch} = {opening+new-dispatch}.'
        final=f'После поступления {opening+new} коробок, после отправки {opening+new-dispatch}. Место А7.'
        truth=dict(direction='forward',inputs=[opening,new,dispatch],outputs=[opening+new,opening+new-dispatch])
    else:
        target,old,new,dispatch=100+shift,20,35,25
        request=(f'После отправки {dispatch} коробок должно остаться {target}. Перед отправкой поступят '
                 f'не {old}, а {new} коробок. Обновите требуемый начальный запас и запас после поступления. Место хранения — А7.')
        rule=f'{target} + {dispatch} = {target+dispatch}; {target+dispatch} − {new} = {target+dispatch-new}.'
        final=f'Начальный запас {target+dispatch-new}, после поступления {target+dispatch}. Место А7.'
        truth=dict(direction='backward',inputs=[target,new,dispatch],outputs=[target+dispatch-new,target+dispatch])
    return dict(request=request,rule=rule,final=final,truth=truth)


def selection(topic,variant,exposure=False):
    if topic not in ('schedule','inventory') or variant not in (0,1):raise ValueError('Unknown selection stimulus')
    threshold=12+(0 if exposure else 4)
    if variant==0:
        values=[threshold-2,threshold,threshold+4];prices=[400,700,900];index=1;constraint='at_least'
        noun='зал' if topic=='schedule' else 'упаковку'
        request=(f'Выберите самый дешёвый вариант: {noun} вместимостью не меньше {threshold}. '
                 f'А: вместимость {values[0]}, 400 ₽; Б: {values[1]}, 700 ₽; В: {values[2]}, 900 ₽. Назовите вариант и цену.')
        rule=f'А не подходит: {values[0]} < {threshold}. Из Б и В дешевле Б: 700 < 900.'
    else:
        values=[threshold+2,threshold,threshold-4];prices=[400,900,700];index=2;constraint='at_most'
        attribute='время доставки оборудования' if topic=='schedule' else 'масса упаковки'
        unit='минут' if topic=='schedule' else 'кг'
        request=(f'Выберите самый дешёвый вариант, у которого {attribute} не больше {threshold} {unit}. '
                 f'А: {values[0]} {unit}, 400 ₽; Б: {values[1]} {unit}, 900 ₽; В: {values[2]} {unit}, 700 ₽. Назовите вариант и цену.')
        rule=f'А не подходит: {values[0]} > {threshold}. Из Б и В дешевле В: 700 < 900.'
    return dict(request=request,rule=rule,final=f'{"АБВ"[index]}, {prices[index]} ₽.',
                truth=dict(constraint=constraint,threshold=threshold,values=values,prices=prices,selected_index=index))


def material(topic,variant,arm,demonstration_order='dependency_first'):
    if topic not in ('schedule','inventory') or variant not in (0,1) or arm not in ARMS or demonstration_order not in PROCESS_ORDERS:
        raise ValueError('Unknown authored stimulus')
    owner=arm.removeprefix('assistant_')
    items={op:(dependency if op=='dependency' else selection)(topic,variant,True) for op in OPERATIONS}
    order=OPERATIONS if demonstration_order=='dependency_first' else tuple(reversed(OPERATIONS))
    steps=[dict(operation=op,actor='assistant' if op==owner else 'component',rule=items[op]['rule']) for op in order]
    request='\n\n'.join(LABELS[op]+': '+items[op]['request'] for op in order)
    process=DISPATCH+'\n\n'+'\n\n'.join(LABELS[x['operation']]+'. '+('Ассистент' if x['actor']=='assistant' else 'Отдельный модуль')+
                    ' выполнил этап: '+x['rule'] for x in steps)
    final='\n\n'.join(LABELS[op]+': '+items[op]['final'] for op in OPERATIONS)
    probes=[]
    for cell in CELLS:
        relation,op_relation=cell.split('_');target=topic if relation=='same' else ('inventory' if topic=='schedule' else 'schedule')
        op=owner if op_relation=='same' else next(x for x in OPERATIONS if x!=owner)
        item=(dependency if op=='dependency' else selection)(target,variant,False)
        probes.append(dict(id=cell,absolute_id=relation+'_'+op,topic=target,operation=op,**item))
    return dict(exposure_id=f'{topic}-{variant}',topic=topic,variant=variant,arm=arm,
                assistant_operation=owner,demonstration_order=demonstration_order,steps=steps,
                request=request,process=process,final=final,truth={op:items[op]['truth'] for op in OPERATIONS},probes=probes)
