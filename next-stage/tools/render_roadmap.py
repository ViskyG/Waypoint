#!/usr/bin/env python3
"""Derive human plan, assignments and offline preview from ONE authoring graph."""
from pathlib import Path
import argparse, html, json
ROOT=Path(__file__).resolve().parents[1]
def rendered_files():
    p=json.loads((ROOT/'roadmap/ROADMAP.plan.json').read_text())
    packets={k:n for k,n in p['nodes'].items() if n.get('x_roadmap',{}).get('kind')=='packet'}
    edge_list=list(p['edges'].values())
    def req(k,phase):
        return [(e['from'],e['x_observability']['condition']['output_id'],e['x_observability']['why']) for e in edge_list if e['to']==k and e['x_observability']['phase']==phase]
    md=['# Waypoint — дорожная карта следующего этапа','','Производное представление `ROADMAP.plan.json`. Это план, не текущий журнал исполнения.','',
        '**MIXED.** 10 исполнимых пакетов, 1 контейнер и 1 внешний вход; 17 блокирующих связей с результатами/фазами. Не переисполнять C01–C07.','',
        '```text','N00 → N01 → N02 / N03 / N04 / N05 / N07 → N08','N00 → N06 → N08 (темы не ждут нового профиля)',
        'N02 → завершение N03; N06 + референс третьей темы → N09.',
        'N08 нужен для окончательной проверки N09, но N09 НЕ блокирует N08.','```','',
        'Общие файлы интегрируются одним владельцем. Предпочтительный последовательный порядок — не дополнительные логические рёбра.','',
        '| Пакет | Понятный результат | Для начала | Для завершения |','|---|---|---|---|']
    out={}
    for k,n in packets.items():
        x=n['x_roadmap'];intent=n['x_observability']['intent']
        start=', '.join(a for a,_,_ in req(k,'start')) or 'Проверка доступной рабочей копии'
        finish=', '.join(a for a,_,_ in req(k,'finish')) or 'Собственная приёмка'
        md.append(f'| [{k}](packets/{k}.md) | {intent["summary"]} | {start} | {finish} |')
        lines=[f'# {k} — {n["title"]}','','## Для владельца',intent['summary'],'',intent['context'],'',intent['change'],'','## Входы и результат']
        for phase,label in [('start','Для начала'),('finish','Для завершения')]:
            lines+=['',f'**{label}:**']
            dependencies=req(k,phase)
            lines += [f'- {a} / {o}: {why}' for a,o,why in dependencies] or ['Нет дополнительного входного ребра; собственные критерии обязательны.']
        lines += ['', '**Выход:** '+next(iter(n['x_observability']['outputs'].values()))['definition'],'','## Точное чтение','Из корня ЭТОГО архива:']
        lines += ['- '+s for s in x['read_set']]
        lines += ['','В действующем репозитории:']+['- '+s for s in x['repository_read_set']]
        lines += ['','## Владение изменениями']+['- '+s for s in x['owned_paths']]
        lines += ['','Общие файлы — один интегратор. Параллельный исполнитель готовит адресный вклад, не заменяет общий файл целиком.','',
                  '## Исполнение']+[f'{i+1}. {s}' for i,s in enumerate(x['actions'])]
        lines += ['','## Приёмка']+[f'- **{k}/{aid}:** {a["text"]}' for aid,a in n['acceptance'].items()]
        lines += ['','Не отмечать эти критерии прошедшими по наличию теста в архиве. Целевая реализация и интеграция ещё должны их выполнить.','',
                  '## Маршрут и продолжение',f'Предпочтительный исполнитель: {x["preferred_executor"]}.',
                  x.get('eligible_alternative') or 'Нет обязательной поставки из чата; Codex выполняет этот же пакет.',
                  'Условие эскалации: '+x['escalation']+'.',
                  'После собственного результата взять следующий узел с доступными входами и свободной областью изменений. Не занимать сразу несколько будущих пакетов.']
        if k=='WPT-N09':lines+=['','При отсутствии референса — AWAITING_REFERENCE. Не создавать дубликат темы и не объявлять весь этап завершённым.']
        out['roadmap/packets/'+k+'.md']='\n'.join(lines)+'\n'
    md+=['','## Что не делает эта карта','Она не запускает Codex/Runner/расписание, не задаёт реальные статусы и не содержит вымышленных агентов. Идентификаторы нового этапа добавляются к свежему экспорту через подготовленный guarded merge.','',
         '## Важные различия','Ввод референса — условие результата, не назначение платного исполнителя. Реализация пакета, прохождение приёмки, публикация скила и его установка — разные факты.','',
         '## Новый этап в работающем проекте','Не импортировать этот stage-only JSON как весь существующий проект. См. `../CODEX_START.md` и `../tools/prepare_stage_merge.py`.']
    out['roadmap/ROADMAP.md']='\n'.join(md)+'\n'
    out['roadmap/RUNNER_WAVES.md']='''# Волны того же графа, не отдельная очередь

RW-00: N00 — актуальная рабочая база, приватный backup/экспорт; требует целевого доступа.
RW-01: N01 — общий профиль/фикстуры/миграция. Стабилизировать контракт до параллельных вкладов.
RW-02: N02–N05/N07 — адресные вклады по фиксированным контрактам; N06 может готовиться уже после N00; общий store/API/UI-shell интегрирует один владелец.
RW-03: N08 — объединённая миграция и настоящая browser/service приёмка.
RW-04: N09 — третья тема по её референсу, затем только затронутые проверки.

Это производная группировка ROADMAP.plan.json. Runner — только алгоритмический исполнитель
по уже установленному протоколу. Архив не выдумывает его команды/схему, не пишет в
command inbox и не создаёт новое расписание. Offline можно готовить кандидаты из
известных исходников, но не объявлять их применёнными к недоступной рабочей базе.
На возврате машины сначала сверить актуальные local/Git/принятые представления.

При наличии живого claim не дублировать его файлы. Если чатов нет, Codex выполняет
ту же последовательность. Нет обязательного ожидания ChatGPT и параллельной карты.
'''
    # Small read-only view. Data and labels are taken from same graph. No fake runtime.
    encoded=json.dumps(p,ensure_ascii=False).replace('<','\\u003c')
    h='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Waypoint · следующий этап</title>
<style>body{margin:0;background:#f4f0e9;color:#2d2825;font:15px/1.55 system-ui,sans-serif}header{padding:24px 32px;border-bottom:1px solid #cdbfb3}h1{font-size:26px;margin:0}p{max-width:1000px}main{display:grid;grid-template-columns:minmax(290px,1fr) minmax(450px,1.6fr);gap:24px;padding:24px 32px}nav{display:flex;flex-direction:column;gap:9px}button{font:inherit;text-align:left;border:1px solid #d7c9bd;background:#fffaf5;border-radius:9px;padding:14px;cursor:pointer}button[aria-current=true]{border:2px solid #a45338}small{display:block;color:#77675f}.card{background:#fffaf5;padding:24px;border:1px solid #d7c9bd;border-radius:12px}h2{margin-top:0}h3{font-size:17px;margin-bottom:7px}li{margin:8px 0}code{white-space:pre-wrap;font-size:13px}.muted{color:#77675f}.tag{border:1px solid #bda899;padding:3px 8px;border-radius:5px}details{margin:18px 0}summary{cursor:pointer}#flow{padding:15px 32px;font-family:monospace;background:#e9e0d7;white-space:pre-wrap}a{color:#8f4630}@media(max-width:850px){main{display:block;padding:15px}nav{margin-bottom:24px}}</style>
<header><h1>Waypoint · следующий этап</h1><p>Предпросмотр проектных заданий. Не новая версия приложения и не живой монитор. <span class="tag">MIXED</span></p><span class="muted">10 пакетов · один граф · третья тема ждёт референса · исполнение не запускалось</span></header>
<div id="flow">N00 → N01 → [N02 · N03 · N04 · N05 · N07] → N08
N00 → N06 → N08 (темы независимы от нового профиля)
N02 → завершение N03   |   N06 + выбранный референс → N09; N08 → проверка N09</div>
<main><nav id="list" aria-label="План работ"></nav><article id="detail" class="card"></article></main>
<script>const PLAN=__DATA__;
const packets=Object.entries(PLAN.nodes).filter(([id,n])=>n.x_roadmap?.kind==='packet');
const el=(t,txt)=>{const e=document.createElement(t);if(txt!==undefined)e.textContent=txt;return e};
function section(root,title,items){root.append(el('h3',title));const ul=el('ul');for(const x of items)ul.append(el('li',x));root.append(ul)}
function show(id){const n=PLAN.nodes[id],d=document.getElementById('detail');d.replaceChildren();
 for(const b of document.querySelectorAll('#list button'))b.setAttribute('aria-current',b.dataset.id===id?'true':'false');
 d.append(el('small',id),el('h2',n.title));const i=n.x_observability.intent;d.append(el('p',i.summary),el('p',i.context),el('p',i.change));
 const es=Object.values(PLAN.edges).filter(e=>e.to===id);section(d,'Требуемые входные результаты',es.map(e=>`${e.x_observability.phase==='finish'?'Для завершения':'Для начала'}: ${e.from} / ${e.x_observability.condition.output_id}. ${e.x_observability.why}`));
 section(d,'Условия приёмки',Object.entries(n.acceptance).map(([k,v])=>k+' · '+v.text));
 const det=el('details');det.append(el('summary','Для исполнителя: действия, чтение и файлы'));section(det,'Действия',n.x_roadmap.actions);section(det,'Контракты в архиве',n.x_roadmap.read_set);section(det,'Владение изменениями',n.x_roadmap.owned_paths);d.append(det);
 d.append(el('p',id==='WPT-N09'?'Не начинать с выдуманным референсом. Остальной этап от этого не зависит.':'Фактический статус появится после исполнения. Проверки здесь пока только запланированы.'));
 const a=el('a','Открыть текст задания');a.href='packets/'+id+'.md';d.append(a);location.hash=id;}
for(const [id,n] of packets){const b=el('button');b.dataset.id=id;b.append(el('strong',id+' · '+n.title),el('small',n.x_observability.intent.summary));b.onclick=()=>show(id);document.getElementById('list').append(b)}
show(PLAN.nodes[location.hash.slice(1)]?.x_roadmap?.kind==='packet'?location.hash.slice(1):packets[0][0]);
</script></html>'''.replace('__DATA__',encoded)
    out['roadmap/PREVIEW.html']=h+'\n'
    return out

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--check',action='store_true');args=a.parse_args()
    bad=[]
    for name,body in rendered_files().items():
        q=ROOT/name
        if args.check:
            if not q.exists() or q.read_text()!=body:bad.append(name)
        else:q.parent.mkdir(parents=True,exist_ok=True);q.write_text(body,encoding='utf-8')
    if bad:a.exit(1,'Derived views differ: '+', '.join(bad)+'\n')
    print('DERIVED_VIEWS_OK' if args.check else 'RENDERED_FROM_ONE_GRAPH')
if __name__=='__main__':main()
