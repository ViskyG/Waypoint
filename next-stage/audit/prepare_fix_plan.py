#!/usr/bin/env python3
"""Prepare bounded audit remediation from a fresh export; never writes a service."""
import argparse,copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'waypoint'))
from waypoint.domain import digest,validate_plan
FIXES=[
 ('WPT-N04-FIX','WPT-N04','Исправить согласование и восстановление окон чтения',['CONTRACT-F01','CONTRACT-F05','CONTRACT-F06'],['web/app.js','web/filters.js','focused HTTP/browser regressions'],[
 'Исправленное из видимого типа сообщение исчезает из старого отфильтрованного окна; API и DOM согласованы.',
 'Якорь сообщения и смещение сохраняются при изменении высоты и возврате к ранее открытому фильтру.',
 'Общий фильтр по умолчанию задаёт новые окна, сохраняя независимые настройки существующих.']),
 ('WPT-N02-FIX','WPT-N02','Сохранить контекст связей и точное основание предпосылок',['CONTRACT-F02','CONTRACT-F03'],['read_models.py','server.py','web/app.js','web/plan.js','roadmap/tools/roadmap.py'],[
 'Связи order видны в packet, Плане и карте как порядок, сохраняя отсутствие блокировки; partial endpoints подписаны.',
 'Основание prerequisites отражает реально использованную рабочую копию, включая node-local и explicit override.']),
 ('WPT-N03-FIX','WPT-N03','Показывать давность связи с источником',['CONTRACT-F04'],['read_models.py','web/projects.js'],[
 'Давно полученное connected отличается от свежего соединения; возраст и активность согласованы, исходный факт сохранён.']),
 ('WPT-N05-FIX','WPT-N05','Подключить ограниченную историю доказательств алгоритма',['CONTRACT-F07'],['read_models.py','store.py','web/app.js','web/algorithm_panel.js'],[
 'Из инспектора доступны все страницы истории без молчаливого ограничения первой сотней.',
 'Страница алгоритма использует индексированный отбор до загрузки тел, а список реестра возвращает ограниченные сводки.']),
 ('WPT-N07-FIX','WPT-N07','Закрепить доказательства и границы исполнения',['WF-01','WF-02','WF-03','WF-04','WF-05','WF-06','WF-08'],['project-local lifecycle instructions','versioned evidence artifacts','criterion metadata presentation'],[
 'Текущее доказательство N07 совпадает с закреплённой ревизией; новый receipt сохраняет прошлые события.',
 'Исторические браузерные доказательства восстановлены из подлинного источника либо точно отмечены как недоступные.',
 'В ходе обычной ремонтной работы исполнители заявляют собственные области до работы и снимают их при передаче; прошлые сообщения не перепривязаны по догадке.',
 'Дата и основание старых проверок видны отдельно от текущей приёмки; поздняя регистрация не выдаётся за старый запуск.']),
 ('WPT-N08-FIX','WPT-N08','Принять исправления на совместной рабочей версии',['CONTRACT-F01','CONTRACT-F02','CONTRACT-F03','CONTRACT-F04','CONTRACT-F05','CONTRACT-F06','CONTRACT-F07','WF-07'],['integrated target acceptance','grouped historical warning presentation','safe delivery reports'],[
 'Исправленные отрицательные сценарии пройдены в браузере через HTTP вместе с базовыми сценариями чтения.',
 'Перезапуск сохраняет исправленные состояния и новые события; обычные события настоящего Codex проходят без подмены фикстурой.',
 'Повторные предупреждения одного периода отличимы от независимых инцидентов без удаления raw истории.',
 'Приёмка сообщает оставшийся N09 и недоказанную старую хронологию отдельно; закрыты только подтверждённые исправления.'])]

def prepare(export):
 p=copy.deepcopy(export['plan']);base=export['version']
 if p['project_id']!='waypoint':raise ValueError('Wrong project')
 for index,(nid,parent,title,findings,owned,tests) in enumerate(FIXES):
  if nid in p['nodes']:raise ValueError('Fix already exists; reconcile current head instead of replacing it: '+nid)
  refs=['audit/CONFORMANCE_RU.md','audit/CONTRACT_FINDINGS.json','audit/WORKFLOW_FINDINGS.json','skills/conformance/WAYPOINT_WORKFLOW.md']
  p['nodes'][nid]={'title':title,'parent':parent,'assignment':f'Ограниченное исправление {parent} по аудиту. Читать из next-stage/: '+', '.join(refs)+'. Находки: '+', '.join(findings)+'. Владение от waypoint/waypoint/: '+', '.join(owned)+'. Не повторять завершённые пакеты и не перепроектировать систему. Общие файлы интегрирует один владелец; конкурирующие writers не запускаются. Прежние доказательства сохранять. Эта запись планирует ремонт и не утверждает его выполнение.',
   'source_refs':[{'label':'Audit evidence','uri':r} for r in refs],
   'acceptance':{f'A{i:02d}':{'text':text} for i,text in enumerate(tests,1)},
   'tests':{f'T{i:02d}':{'label':text,'procedure':'Адресный сценарий по указанной находке и сохранение фактического результата с уровнем доказательства.','invalidated_by':'Изменение соответствующего механизма, запроса, источника или основания.'} for i,text in enumerate(tests,1)},
   'layout':{'x':0,'y':0},'x_roadmap':{'kind':'packet','preferred_executor':'CODEX','reference_root':'../next-stage','audit_findings':findings,'owned_paths':owned,'execution_state_at_authoring':'PLANNED_NOT_EXECUTED','shared_file_policy':'one integration owner for overlapping web/API files'},
   'x_observability':{'intent':{'summary':title,'context':'Аудит выявил расхождения между принятым контрактом и фактическим поведением или доказательствами.','change':'Устранить только указанные расхождения, сохранив работающую реализацию и неизменяемую историю.'},'outputs':{'O-FIXED':{'definition':title+'; выполненные адресные проверки и проверяемые свидетельства','revision':1}}}}
 for nid,*_ in FIXES[:-1]:
  eid=nid+'-TO-N08-FIX';p['edges'][eid]={'from':nid,'to':'WPT-N08-FIX','x_observability':{'relation':'requires','phase':'finish','target_scope':'node','why':'Для завершения совместной приёмки нужен проверенный результат этого исправления.','condition':{'output_id':'O-FIXED','revision':1,'workspace':'project'}}}
 p['x_roadmap']['workflow_profile']='../next-stage/skills/conformance/WAYPOINT_WORKFLOW.md'
 p['x_roadmap'].setdefault('audits',{})['2026-10-17-conformance']={'base_version':base,'report':'../next-stage/audit/CONFORMANCE_RU.md','implementation_changed_by_audit':False}
 validate_plan(p)
 return {'plan':p,'base_version':base,'request_id':'conformance-fixes-'+digest([base,p])[:24],'merge':False}

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--export',type=Path,required=True);a.add_argument('--out',type=Path,required=True);args=a.parse_args()
 body=prepare(json.loads(args.export.read_text()))
 with args.out.open('x') as f:json.dump(body,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'prepared':True,'base':body['base_version'],'nodes':len(body['plan']['nodes']),'request_id':body['request_id']}))
