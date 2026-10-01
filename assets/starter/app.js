(() => {
  'use strict';
  const d=window.RESUME_DATA;
  if(!d){document.body.append(Object.assign(document.createElement('p'),{textContent:'未找到 profile.js，请将完整网站文件放在同一个目录。'}));return;}
  const q=s=>document.querySelector(s),all=s=>[...document.querySelectorAll(s)];
  const node=(tag,text='',cls='')=>{const e=document.createElement(tag);e.textContent=text;if(cls)e.className=cls;return e;};
  const list=value=>Array.isArray(value)?value:[];
  const safeURL=value=>{if(typeof value!=='string'||!value.trim())return '';const s=value.trim();if(/[\u0000-\u001f\u007f\\]/.test(s)||s.startsWith('//'))return '';if(/^(https?:|mailto:|tel:)/i.test(s))return s;if(/^[a-z][a-z\d+.-]*:/i.test(s)||s.startsWith('//'))return '';return s;};
  function link(text,url){const a=node('a',text);a.href=safeURL(url)||'#';if(/^https?:/i.test(a.getAttribute('href'))){a.target='_blank';a.rel='noopener noreferrer';}return a;}
  function downloadLink(){const a=link(d.resume?.file?'下载完整简历 ↓':'查看完整履历 ↗',d.resume?.file||'resume.html');if(d.resume?.file){a.download=d.resume.filename||d.resume.file.split('/').pop();a.dataset.download='true';}return a;}
  document.title=(d.name||'个人')+' · '+(document.body.classList.contains('reader')?'完整履历':d.role||'履历与作品');
  q('#draft-note').hidden=!d.draft;
  if(d.theme){for(const [key,css] of [['accent','--accent'],['background','--bg']]){if(/^#[\da-f]{6}$/i.test(d.theme[key]||''))document.documentElement.style.setProperty(css,d.theme[key]);}}

  function fullResume(){
    const sheet=q('#resume-content');sheet.append(node('h1',d.name),node('p',[d.role,d.location].filter(Boolean).join(' · '),'resume-role'),node('p',d.intro));
    const section=(title,items,draw)=>{if(!items.length)return;sheet.append(node('h2',title));items.forEach(draw);};
    section('个人介绍',list(d.about),t=>sheet.append(node('p',t)));
    section('专业方向',list(d.directions),v=>sheet.append(node('h3',v.title),node('p',v.detail)));
    section('代表性成果',list(d.metrics),v=>sheet.append(node('h3',v.value+' · '+v.label),node('p',v.context,'meta')));
    section('职业经历',list(d.experience),v=>{sheet.append(node('h3',v.period+' · '+v.organization),node('p',[v.role,v.location].filter(Boolean).join(' · '),'meta'));const ul=node('ul');list(v.points).forEach(t=>ul.append(node('li',t)));sheet.append(ul);});
    section('项目作品',list(d.projects),v=>{sheet.append(node('h3',v.title),node('p',v.category,'meta'),node('p',v.description));if(safeURL(v.url))sheet.append(link('查看项目',v.url));});
    section('专业能力',list(d.skills),v=>sheet.append(node('h3',v.name),node('p',v.detail)));
    section('教育经历',list(d.education),v=>sheet.append(node('h3',v.school),node('p',v.detail)));
    section('进一步了解',list(d.contact).filter(v=>safeURL(v.url)),v=>{const p=node('p');p.append(link(v.label,v.url));sheet.append(p);});
    q('#print-resume').addEventListener('click',()=>window.print());
    if(d.resume?.file)q('.reader-bar').append(downloadLink());
  }
  if(document.body.classList.contains('reader')){fullResume();return;}
  document.body.dataset.layout=['overlay','split','type'].includes(d.layout)?d.layout:'overlay';
  all('[data-name]').forEach(e=>e.textContent=d.name||'个人履历');q('[data-role]').textContent=d.role||'';
  q('.title-first').textContent=d.headline?.[0]||d.role||'';q('.title-second').textContent=d.headline?.[1]||d.name||'';
  q('.hero-intro').textContent=d.intro||'';q('.hero-note').textContent=[d.name,d.location].filter(Boolean).join(' · ');
  if(safeURL(d.photo)){const img=q('.portrait img');img.src=d.photo;img.alt=d.photoAlt||d.name+'的肖像';img.hidden=false;q('.portrait-placeholder').hidden=true;img.addEventListener('error',()=>{img.hidden=true;q('.portrait-placeholder').hidden=false;});}
  all('.resume-link').forEach(a=>{const replacement=downloadLink();replacement.className=a.className;a.replaceWith(replacement);});
  const fill=(selector,items,draw)=>{const target=q(selector);if(!items.length){const section=target.closest('.section');if(section&&!['about','contact'].includes(section.id))section.hidden=true;return;}items.forEach(item=>target.append(draw(item)));};
  fill('#direction-list',list(d.directions),v=>{const a=node('article','','direction-card');a.append(node('h3',v.title),node('p',v.detail));return a;});
  fill('#about-copy',list(d.about),v=>node('p',v));
  fill('#education-list',list(d.education),v=>{const a=node('div');a.append(node('h3',v.school),node('p',v.detail));return a;});
  if(!list(d.education).length)q('#education-list').hidden=true;
  fill('#metric-list',list(d.metrics),v=>{const a=node('div','','metric');a.append(node('strong',v.value),node('p',v.label),node('small',v.context));return a;});
  if(!list(d.metrics).length)q('#metric-list').hidden=true;
  fill('#experience-list',list(d.experience),v=>{const a=node('article','','experience-row'),heading=node('div'),ul=node('ul');heading.append(node('h3',v.organization),node('p',[v.role,v.location].filter(Boolean).join(' · '),'role'));list(v.points).forEach(t=>ul.append(node('li',t)));a.append(node('span',v.period),heading,ul);return a;});
  fill('#project-list',list(d.projects),v=>{const a=node('article','','project-card');a.append(node('p',v.category,'kicker'),node('h3',v.title),node('p',v.description));if(safeURL(v.url))a.append(link('查看项目 ↗',v.url));return a;});
  if(q('#projects').hidden){q('.hero-actions .primary').href='resume.html';q('.hero-actions .primary').textContent='查看完整经历 ↗';}
  fill('#skill-list',list(d.skills),v=>{const a=node('div','','skill-row');a.append(node('h3',v.name),node('p',v.detail));return a;});
  fill('#contact-links',list(d.contact).filter(v=>safeURL(v.url)),v=>link(v.label+' ↗',v.url));q('#contact-links').append(downloadLink());
  const navItems=[['home','首页'],['directions','专业方向'],['about','关于我'],['experience','职业经历'],['projects','项目作品'],['skills','专业能力'],['contact','进一步了解']].filter(([id])=>!q('#'+id).hidden);
  navItems.forEach(([id,title],i)=>{q('.desktop-nav').append(link(title,'#'+id));const a=link(title,'#'+id);a.append(node('small',String(i+1).padStart(2,'0')));q('.mobile-menu').append(a);});
  const navDownload=downloadLink();navDownload.append(node('small',String(navItems.length+1).padStart(2,'0')));q('.mobile-menu').append(navDownload);
  q('.hero-under>a').href='#'+(navItems[1]?.[0]||'about');
  const menu=q('#mobile-menu'),toggle=q('.menu-toggle');
  function closeMenu(){menu.hidden=true;toggle.setAttribute('aria-expanded','false');toggle.setAttribute('aria-label','打开导航');}
  toggle.addEventListener('click',()=>{const open=menu.hidden;menu.hidden=!open;toggle.setAttribute('aria-expanded',String(open));toggle.setAttribute('aria-label',open?'关闭导航':'打开导航');});
  menu.addEventListener('click',e=>{if(e.target.closest('a'))closeMenu();});
  addEventListener('keydown',e=>{if(e.key==='Escape'&&!menu.hidden){closeMenu();toggle.focus();}});
  matchMedia('(min-width:1051px)').addEventListener('change',e=>{if(e.matches)closeMenu();});
  const dialog=q('#download-dialog');let downloadOrigin;
  document.addEventListener('click',e=>{const a=e.target.closest('a[data-download]');if(!a||e.defaultPrevented||e.button!==0)return;downloadOrigin=menu.contains(a)?toggle:a;q('#download-name').textContent=a.download;if(!dialog.open)dialog.showModal();});
  q('.dialog-close').addEventListener('click',()=>dialog.close());dialog.addEventListener('close',()=>downloadOrigin?.focus());dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();}});

  // Every run has an owner; returning, replaying or pausing cancels the previous one.
  const hero=q('.hero'),reduce=matchMedia('(prefers-reduced-motion: reduce)');let run=0,state='idle',animations=[];
  function finish(next='complete'){run++;state=next;animations.forEach(a=>a.cancel());animations=[];}
  async function play(){
    if(state!=='idle'||reduce.matches||document.hidden||!Element.prototype.animate)return;
    state='preparing';const token=++run,img=q('.portrait img');
    if(!img.hidden)await Promise.race([img.decode().catch(()=>{}),new Promise(resolve=>setTimeout(resolve,800))]);
    if(token!==run)return;if(document.hidden||reduce.matches||hero.getBoundingClientRect().top < -100){finish('idle');return;}
    state='playing';
    const animate=(e,frames,duration,delay=0,options={})=>{const a=e.animate(frames,{duration,delay,fill:'both',easing:'cubic-bezier(.22,1,.36,1)',...options});animations.push(a);return a;};
    const rise=(selector,delay,distance=15)=>animate(q(selector),[{opacity:0,transform:`translateY(${distance}px)`},{opacity:1,transform:'none'}],760,delay);
    rise('.hero-top',0,5);rise('.portrait',250);rise('.title-first',450);rise('.title-second',800);rise('.hero-note',1100,8);rise('.hero-bottom',1300);rise('.hero-under',1500,5);
    animate(q('.entrance-line path'),[{strokeDasharray:'1',strokeDashoffset:1},{strokeDasharray:'1',strokeDashoffset:0}],1300,0,{easing:'linear'});
    const end=animate(q('.entrance-line'),[{opacity:0,offset:0},{opacity:.7,offset:.15},{opacity:.5,offset:.65},{opacity:0,offset:1}],3000,0);
    end.finished.then(()=>{if(token===run)finish();},()=>{});
  }
  function sync(){const r=hero.getBoundingClientRect();if(reduce.matches||document.hidden){finish('idle');return;}if(r.top>=-100&&r.top<innerHeight*.4)play();else if(r.bottom<120&&state!=='idle')finish('idle');}
  q('.replay').addEventListener('click',()=>{finish('idle');play();});
  document.addEventListener('click',e=>{if(e.target.closest('a[href="#home"]')){finish('idle');requestAnimationFrame(sync);}});
  document.addEventListener('focusin',e=>{if(hero.contains(e.target)&&state==='playing'&&!e.target.closest('.replay'))finish();});
  document.addEventListener('visibilitychange',sync);reduce.addEventListener('change',sync);
  let scrollFrame=0;function queue(){if(!scrollFrame)scrollFrame=requestAnimationFrame(()=>{scrollFrame=0;sync();});}
  addEventListener('scroll',queue,{passive:true});addEventListener('resize',queue,{passive:true});addEventListener('hashchange',queue);addEventListener('pageshow',queue);
  addEventListener('beforeprint',()=>finish());sync();
})();
