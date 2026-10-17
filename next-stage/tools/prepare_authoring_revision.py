#!/usr/bin/env python3
"""Prepare intent backfill and curated real-code catalogue from a fresh export.

No service writes, no inferred test runs, no layout/status/assignment rewrites.
Implementation revisions pin exact bytes, including uncommitted integration work.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

INTENTS={
'WPT-BASE':('Поставленная основа наблюдателя','В проект уже переданы ядро, адаптер, браузерный интерфейс и инструменты.','Использовать существующие части как основу следующих изменений, сохранив идентификаторы и данные.'),
'WPT-C01':('Хранить карту и историю надёжно','План и наблюдения должны переживать повторную доставку и перезапуск.','Сохранить версионную карту, неизменяемый журнал и совместимый API с защищённым доступом.'),
'WPT-C02':('Получать события Codex','Источник сообщает об агентах и сообщениях через собственные артефакты Codex.','Преобразовывать доступные факты в наблюдения Waypoint, сохраняя происхождение и отсутствие данных.'),
'WPT-C03':('Читать работу на карте','Владельцу нужен наглядный доступ от блока к агентам и сообщениям.','Показывать вложенную карту и инспектор существующих событий без управления исполнителем.'),
'WPT-C04':('Передавать карты и подключать инструменты','Дорожную карту нужно переносить между автором и локальным наблюдателем.','Дать CLI, проектные инструкции и переносимый формат с сохранением идентификаторов.'),
'WPT-C05':('Связать Waypoint с действующим Codex','Живой источник требует точных идентификаторов, привязок и восстановления.','Наблюдать текущих исполнителей и доставлять их события без потери или подмены истории.'),
'WPT-C05.1':('Определять исполнителя и участок работы','Родительский процесс и подагент могут работать одновременно в разных блоках.','Сопоставлять собственную идентичность исполнителя с явной границей его рабочего участка.'),
'WPT-C05.2':('Доставлять поток с восстановлением','Повторная доставка и перезапуск не должны терять или дублировать факты.','Читать источник инкрементально и сохранять подтверждения доставки вместе с курсором.'),
'WPT-C05.3':('Находить сообщения по привязкам','Одно сообщение может относиться к нескольким блокам, включая потомков.','Индексировать привязки и выдавать устойчивые страницы без повторов и произвольного ограничения истории.'),
'WPT-C05.4':('Проверить источник на настоящем Codex','Модельные фикстуры не доказывают подключение к текущей сессии.','Сверить реальные идентификаторы, сообщения и связи с доступными фактами работающего Codex.'),
'WPT-C06':('Читать живую карту непрерывно','Во время чтения приходят новые сообщения и меняются состояния.','Обновлять нужные части интерфейса, сохраняя место чтения и доступ к вложенным исполнителям.'),
'WPT-C06.1':('Сохранить место чтения сообщений','Новые сообщения могут сдвинуть старый текст или выделение при копировании.','Согласовывать сообщения по устойчивой идентичности и показывать новые записи отдельно.'),
'WPT-C06.2':('Обновлять нужные части вложенной карты','События одного исполнителя не должны перестраивать всю открытую карту.','Применять выборочные обновления и показывать вложенных агентов через их настоящие связи.'),
'WPT-C06.3':('Проверить насыщенную карту в браузере','Небольшой пример не выявляет проблемы при большом числе блоков и сообщений.','Проверить читательские сценарии через настоящий сервис и браузер на репрезентативной карте.'),
'WPT-C07':('Принять единую локальную сборку','Изменения адаптера и интерфейса должны работать совместно.','Объединить существующие результаты и подтвердить локальную работу и передачу владельцу.'),
'WPT-C07.1':('Собрать совместимые компоненты','Отдельно работающие части могут расходиться по контрактам.','Проверить единую сборку с согласованными зависимостями и сохранёнными данными.'),
'WPT-C07.2':('Проверить путь от блока до браузера','Доказательство подключения требует пройти весь путь реального события.','Связать блок, настоящего агента, журнал и отображение сообщения в браузере.'),
'WPT-C07.3':('Сделать карты переносимыми','Будущие проекты должны использовать один граф без ручного переписывания заданий.','Описать профиль авторства и проверить перенос плана с сохранением структуры и расширений.'),
'WPT-C07.4':('Передать результат владельцу','Работа должна сопровождаться воспроизводимым запуском и честными ограничениями.','Подготовить исходники, инструкции и отчёт с разделением реальных проверок и открытых вопросов.'),
'WPT-R00':('Принять исходную базу без потери истории','Перед продолжением нужно знать фактическое состояние исходников и доступных проверок.','Подготовить рабочую копию и импортировать утверждённую карту в существующий Waypoint.')}


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def algorithm(aid,title,purpose,paths,tests,inputs,outputs,steps,invariants,edge_cases,risks,root):
    source=[]
    for path,symbol in paths:
        raw=(root/path).read_bytes()
        if symbol.split('.')[-1].encode() not in raw:raise ValueError('Missing source symbol: '+symbol)
        source.append([path,hashlib.sha256(raw).hexdigest()])
    for path,symbol in tests:
        raw=(root/path).read_bytes()
        if symbol and symbol.encode() not in raw:raise ValueError('Missing test symbol: '+symbol)
    return {'id':aid,'title':title,'purpose':purpose,'inputs':inputs,'outputs':outputs,'steps':steps,'invariants':invariants,'edge_cases':edge_cases,
            'definition_revision':1,'implementation':{'repository':'https://github.com/ViskyG/Waypoint','revision':'worktree-sha256:'+digest(source),'refs':[{'path':p,'symbol':s} for p,s in paths]},
            'testability':{'strategy':'Запускать указанные проверки при изменении соответствующего механизма; наличие ссылки не означает выполненный запуск. Точные результаты хранятся отдельно в журнале наблюдений.',
                           'test_refs':[{'path':p,**({'symbol':s} if s else {})} for p,s in tests], 'missing_cases':['Текущие измерения производительности и целевые свидетельства не выводятся из наличия тестового файла.']},'resource_risks':risks}


def _legacy_inventory(root):
    return {
    'plan-three-way-merge':algorithm('plan-three-way-merge','Трёхстороннее согласование карты','Объединить независимые изменения, сохранив конфликтующие различия для явного решения.',
        [('waypoint/waypoint/domain.py','three_way')],[('waypoint/tests/test_core.py','test_merge_disjoint_and_conflicting'),('waypoint/tests/test_core.py','test_delete_vs_new_reference_conflict')],
        ['Общая базовая версия','Текущая карта','Предложенная карта'],['Согласованная карта','Конкретные конфликты по путям'],['Сравнить базовое, текущее и предложенное значения','Рекурсивно согласовать словари','Сохранить несовместимые изменения как конфликты'],['Не затирать независимые изменения','Одинаковое предложение даёт одинаковый результат'],['Удаление против нового изменения','Неизвестные расширения','Одинаковые изменения с обеих сторон'],['Стоимость обхода зависит от размера карты'],root),
    'effective-prerequisites':algorithm('effective-prerequisites','Эффективные входные требования','Показать реальные входные результаты с учётом области, фазы, версии и свидетельств.',
        [('waypoint/waypoint/dependencies.py','effective_requirements'),('waypoint/waypoint/dependencies.py','evaluate_availability')],[('waypoint/tests/test_dependencies.py',None)],
        ['Граф с типизированными рёбрами','Потребитель и фаза','Свидетельства и рабочая область'],['Эффективные требования','Состояния доступности с происхождением'],['Развернуть явные связи и наследуемые subtree-условия','Вычислить отпечаток смысла входа','Сопоставить свидетельства и сохранить неизвестность или конфликт'],['Статус done не подтверждает наличие входа','Позиция на карте не меняет отпечаток','Все обязательные входы рассматриваются совместно'],['Конфликтующие источники','Изменённый смысл выхода','Поздняя доставка','Неизвестная рабочая область'],['Обход вложенности и свидетельств должен оставаться ограниченным запросом'],root),
    'item-target-paging':algorithm('item-target-paging','Выбор сообщений и устойчивая пагинация','Найти подходящие записи во всей истории без повторов по нескольким привязкам.',
        [('waypoint/waypoint/store.py','Store.items')],[('waypoint/tests/test_targets_binding.py','test_chunked_descendants_many_targets_and_stable_page'),('waypoint/tests/test_core.py','test_item_pagination_is_stable')],
        ['Проект, область и фильтры','Индекс привязок','Граница страницы'],['Упорядоченная уникальная страница','Курсор следующей страницы'],['Отобрать подходящие идентичности до лимита','Исключить повторы по нескольким привязкам','Применить устойчивую границу и загрузить тела записей'],['Фильтр не меняет сбор истории','Одна собственная идентичность видна один раз','Курсор привязан к параметрам запроса'],['Много потомков','Неизвестные типы','Исправленные привязки','Пустой фильтр'],['Загрузка тел до отбора может раздувать память','Широкие области требуют индексированного отбора'],root),
    'anchored-message-reconciliation':algorithm('anchored-message-reconciliation','Согласование сообщений без потери чтения','Сохранять текущий текст, выделение и место чтения при поступлении обновлений.',
        [('waypoint/waypoint/web/app.js','patchMessage'),('waypoint/waypoint/web/app.js','paintReader')],[('waypoint/tests/rich_browser_check.py',None)],
        ['Существующие DOM-узлы по идентичности','Новые версии сообщений','Якорь и состояние читателя'],['Обновлённый поток','Сохранённое выделение и место чтения','Отдельный счётчик новых сообщений'],['Сопоставить записи по устойчивому ключу','Отложить изменение выделенного текста','Обновить изменившиеся элементы и восстановить якорь'],['Не пересоздавать выбранный текст','Новые сообщения не отрывают читателя от старых','Состояние окна независимо от других читателей'],['Изменение существующей записи','Дозагрузка старой страницы','Переключение фильтра','Отключение и восстановление источника'],['Слишком большой DOM замедляет читательское окно'],root)}


# These are the only accidental aliases introduced by the first helper revision.
ALIASES={'plan-three-way-merge':'ALG-MERGE','effective-prerequisites':'ALG-DEPS',
         'item-target-paging':'ALG-PAGE','anchored-message-reconciliation':'ALG-READ'}


def _supplied_definitions():
    return json.loads((ROOT/'next-stage/roadmap/ROADMAP.plan.json').read_text())['x_observability']['algorithms']


def inventory(root):
    """Keep the supplied stable identity/meaning; enrich with inspected actual code."""
    baseline=_supplied_definitions()
    result={}
    for alias,actual in _legacy_inventory(root).items():
        aid=ALIASES[alias]
        definition=copy.deepcopy(baseline[aid])
        definition['implementation']=actual['implementation']
        definition['testability']=actual['testability']
        result[aid]=definition
    return result


def _enrich(existing, desired):
    """Overlay known fields while retaining unknown extensions, including refs."""
    if isinstance(existing,dict) and isinstance(desired,dict):
        result=copy.deepcopy(existing)
        for key,value in desired.items():result[key]=_enrich(existing.get(key),value)
        return result
    if isinstance(existing,list) and isinstance(desired,list) and all(isinstance(x,dict) and 'path' in x for x in desired):
        result=[]
        for value in desired:
            old=next((x for x in existing if isinstance(x,dict) and x.get('path')==value['path'] and (not x.get('symbol') or x.get('symbol')==value.get('symbol'))),{})
            result.append(_enrich(old,value))
        return result
    return copy.deepcopy(desired)


def _recognized_alias(definition, expected):
    # Worktree pins legitimately change after shared source edits. Every other
    # helper-owned field must still match before this bounded alias is removed.
    for key,value in expected.items():
        actual=definition.get(key)
        if key=='implementation' and isinstance(actual,dict):
            actual={k:v for k,v in actual.items() if k!='revision'}
            value={k:v for k,v in value.items() if k!='revision'}
        if actual!=value:return False
    return True


def _reconcile_inventory(algorithms,root):
    aliases=_legacy_inventory(root)
    supplied=_supplied_definitions()
    removed={}
    for alias,aid in ALIASES.items():
        if alias not in algorithms:continue
        old=algorithms[alias]
        if not _recognized_alias(old,aliases[alias]):
            raise ValueError('Alias ID contains non-helper changes; reconcile explicitly: '+alias)
        removed[alias]=copy.deepcopy(old)
    for aid,desired in inventory(root).items():
        existing=algorithms.get(aid)
        if existing is None:
            algorithms[aid]=copy.deepcopy(desired)
            continue
        # Preserve original authored meaning and unknown fields. Enrich only the
        # actual code/testability fields after source/symbol inspection.
        updates={key:desired[key] for key in ('implementation','testability')}
        merged=_enrich(existing,updates)
        changed=merged!=existing
        if changed:
            merged['definition_revision']=existing['definition_revision']+1
            reconciliation=merged.setdefault('x_authoring_reconciliation',{})
            reconciliation.update({'strategy':'preserve canonical supplied identity and authored meaning; enrich inspected implementation/testability',
                'previous_definition_sha256':digest(existing),'supplied_definition_sha256':digest(supplied[aid]),
                'from_revision':existing['definition_revision'],'to_revision':merged['definition_revision']})
        algorithms[aid]=merged
    for alias,old in removed.items():
        aid=ALIASES[alias]
        # Any unknown alias extensions survive on the canonical record; explicit
        # conflicting extension values fail rather than silently overwrite.
        for key,value in old.items():
            if key in aliases[alias]:continue
            if key in algorithms[aid] and algorithms[aid][key]!=value:
                raise ValueError('Alias extension conflict: '+alias+'/'+key)
            algorithms[aid].setdefault(key,copy.deepcopy(value))
        del algorithms[alias]
    return removed


def prepare(export,root=ROOT):
    plan=export.get('plan');version=export.get('version') or export.get('base_version')
    if not isinstance(plan,dict) or not isinstance(version,str) or not version:raise ValueError('Fresh {plan,version} export required')
    if export.get('version') and export.get('base_version') and export['version']!=export['base_version']:raise ValueError('Conflicting base versions')
    if plan.get('project_id')!='waypoint' or plan.get('schema')!='waypoint.plan/1':raise ValueError('This curated migration targets Waypoint only; use transferable template for another project')
    out=copy.deepcopy(plan)
    for node_id,values in INTENTS.items():
        if node_id not in out['nodes']:continue
        x=out['nodes'][node_id].setdefault('x_observability',{})
        # Do not replace an owner's already-authored intent.
        if not x.get('intent'):x['intent']=dict(zip(('summary','context','change'),values))
    profile=out.setdefault('x_observability',{})
    if profile.get('schema') not in (None,'waypoint.observability/1'):raise ValueError('Unknown newer profile')
    profile.setdefault('schema','waypoint.observability/1');profile.setdefault('purpose','Наблюдать работу агентов, карту и проверяемые результаты, сохраняя реальную историю без управления исполнителями.')
    algorithms=profile.setdefault('algorithms',{})
    removed=_reconcile_inventory(algorithms,root)
    # Normalize recognized aliases across every current node. Old plan versions
    # remain immutable in Waypoint; this request never rewrites event history.
    for node in out['nodes'].values():
        node_profile=node.get('x_observability',{})
        if 'algorithm_refs' in node_profile:
            node_profile['algorithm_refs']=list(dict.fromkeys(ALIASES.get(a,a) for a in node_profile['algorithm_refs']))
    refs={'WPT-C01':['ALG-MERGE'],'WPT-C04':['ALG-MERGE'],'WPT-C05.3':['ALG-PAGE'],'WPT-C06.1':['ALG-READ'],
          'WPT-N02':['ALG-DEPS'],'WPT-N04':['ALG-PAGE'],'WPT-N05':['ALG-MERGE','ALG-DEPS','ALG-PAGE','ALG-READ']}
    for node_id,ids in refs.items():
        if node_id in out['nodes']:
            existing=out['nodes'][node_id].setdefault('x_observability',{}).setdefault('algorithm_refs',[])
            existing.extend(a for a in ids if a not in existing)
    return {'plan':out,'base_version':version,'request_id':'waypoint-authoring-'+digest([version,out])[:24],'merge':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--export',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--project-root',type=Path,default=ROOT);a=p.parse_args()
    try:
        body=prepare(json.loads(a.export.read_text()),a.project_root)
        with a.out.open('x') as f:json.dump(body,f,ensure_ascii=False,indent=2);f.write('\n')
        print('PREPARED_ONLY',body['base_version'],body['request_id'])
    except (ValueError,OSError,KeyError) as e:p.exit(2,str(e)+'\n')
