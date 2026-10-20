/* UI-only localization. Authored plans, messages and evidence never enter this catalog. */
(() => {
    'use strict';
    const api=window.WaypointUI=window.WaypointUI || {};
    const storageKey='waypoint-language', catalog={en:{},ru:{}}, listeners=new Set(), missing=new Set();
    let language='en';
    try { const saved=localStorage.getItem(storageKey); if (saved==='en' || saved==='ru') language=saved; } catch {}
    api.registerTranslations=(namespace,translations) => {
        const keys=Object.keys(translations.en || {});
        if (keys.length!==Object.keys(translations.ru || {}).length || keys.some(key=>typeof translations.en[key]!=='string' || typeof translations.ru[key]!=='string')) throw Error('Incomplete UI translations: '+namespace);
        for (const key of keys) {
            const full=namespace+'.'+key;
            const placeholders=value=>[...value.matchAll(/\{(\w+)\}/g)].map(match=>match[1]).sort().join(',');
            if (placeholders(translations.en[key])!==placeholders(translations.ru[key])) throw Error('Inconsistent UI placeholders: '+full);
            if (full in catalog.en) throw Error('Duplicate UI translation: '+full);
            for (const lang of ['en','ru']) catalog[lang][full]=translations[lang][key];
        }
    };
    api.hasTranslation=key=>Object.hasOwn(catalog.en,key);
    api.t=(key,values={}) => {
        const template=catalog[language][key];
        if (template===undefined) {missing.add(key);return key;}
        return template.replace(/\{(\w+)\}/g,(match,name)=>Object.hasOwn(values,name) ? String(values[name]) : match);
    };
    Object.defineProperties(api,{language:{get:()=>language},locale:{get:()=>language==='ru'?'ru-RU':'en-US'}});
    api.onLanguageChange=callback=>{listeners.add(callback);return()=>listeners.delete(callback);};
    api.translationDiagnostics=()=>({language,missing:[...missing],keys:Object.keys(catalog.en),languages:['en','ru']});
    function applyDocument() {
        document.documentElement.lang=language;
        for (const [suffix,attribute] of [['',null],['-title','title'],['-aria-label','aria-label'],['-placeholder','placeholder']]) {
            for (const node of document.querySelectorAll?.('[data-i18n'+suffix+']') || []) {
                const text=api.t(node.getAttribute('data-i18n'+suffix));
                if (attribute) node.setAttribute(attribute,text); else node.textContent=text;
            }
        }
    }
    api.setLanguage=(next,{persist=true}={}) => {
        if (!['en','ru'].includes(next)) next='en';
        if (next===language) return;
        window.dispatchEvent?.(new Event('waypoint:beforelanguagechange'));
        language=next;
        if (persist) {try {localStorage.setItem(storageKey,language);} catch {}}
        applyDocument();
        for (const callback of [...listeners]) callback(language);
        // Restore viewport state only after every mounted module has rebuilt its labels.
        window.dispatchEvent?.(new Event('waypoint:languagechange'));
    };
    api.mountLanguageSelector=select=>{
        select.replaceChildren();
        for (const [value,label] of [['en','English'],['ru','Русский']]) {const option=document.createElement('option');option.value=value;option.textContent=label;select.append(option);}
        select.value=language;select.onchange=()=>api.setLanguage(select.value);
        const off=api.onLanguageChange(()=>{select.value=language;});
        return ()=>{select.onchange=null;off();};
    };
    api.registerTranslations('shell',{
        en:{title:'Waypoint · Work map',projects:'Projects',project:'Project',local:'Local',theme:'Theme',language:'Interface language',agents:'AGENTS',orchestrators:'ORCHESTRATORS',outside:'Outside map',observer:'Observation, no agent control',map:'Map',plan:'Plan',algorithms:'Algorithms',view:'Project view',up:'Go up one level',search:'Find a block…',searchLabel:'Find a block',version:'Plan version',diff:'Plan changes',fit:'Fit map',zoomOut:'Zoom out',zoomIn:'Zoom in',resetZoom:'Reset zoom to 100%',full:'Full screen',graph:'Work graph. Drag empty space to pan; use the wheel to zoom.',dependencies:'Dependencies',close:'Close details',waiting:'Waiting for local service',clear:'Clear selection',wheel:'Wheel · zoom / chat'},
        ru:{title:'Waypoint · Карта работ',projects:'Проекты',project:'Проект',local:'Локально',theme:'Оформление',language:'Язык интерфейса',agents:'АГЕНТЫ',orchestrators:'ОРКЕСТРАТОРЫ',outside:'Вне карты',observer:'Наблюдение, не управление',map:'Карта',plan:'План',algorithms:'Алгоритмы',view:'Вид проекта',up:'На уровень выше',search:'Найти блок…',searchLabel:'Найти блок',version:'Версия плана',diff:'Изменения плана',fit:'Вписать карту',zoomOut:'Уменьшить масштаб',zoomIn:'Увеличить масштаб',resetZoom:'Масштаб 100%',full:'На весь экран',graph:'Граф работ. Перетаскивайте пустое место, колесо меняет масштаб.',dependencies:'Зависимости',close:'Закрыть подробности',waiting:'Ожидание локального сервиса',clear:'Снять выделение',wheel:'Колесо · масштаб / чат'}
    });
    applyDocument();
    window.addEventListener?.('storage',event=>{if(event.key===storageKey)api.setLanguage(event.newValue,{persist:false});});
})();
