import {readFile, writeFile} from 'node:fs/promises';
const [input, output, sourcePath] = process.argv.slice(2);
if (!sourcePath) throw new Error('用法：node scripts/render.mjs episode.json output.html source.json');
const episode = JSON.parse(await readFile(input, 'utf8'));
const source = JSON.parse(await readFile(sourcePath, 'utf8'));
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
if (!episode.original_title || !episode.title || !Array.isArray(episode.sections) || !episode.sections.length) throw new Error('缺少标题或章节');
if (episode.url !== source.url || !/^https:\/\/www\.youtube\.com\/watch\?v=[\w-]{11}$/.test(source.url)) throw new Error('来源网址不一致或无效');
const segments = source.segments;
if (!Array.isArray(segments) || !segments.length) throw new Error('没有来源字幕');
let cursor = 0;
const body = episode.sections.map((section, i) => {
  if (!section.title || !Array.isArray(section.paragraphs) || !section.paragraphs.length) throw new Error('章节为空');
  const paragraphs = section.paragraphs.map(p => {
    if (!p.zh?.trim() || !p.en?.trim() || !Array.isArray(p.source_ids) || !p.source_ids.length) throw new Error('缺少双语正文或来源 ID');
    const referenced = p.source_ids.map(id => {
      const segment = segments[cursor++];
      if (!segment || segment.id !== id) throw new Error('来源遗漏、重复或顺序不一致');
      return segment;
    });
    if (p.en !== referenced.map(s => s.text).join(' ')) throw new Error('英文与来源字幕不一致');
    const seconds = Math.floor(referenced[0].start);
    const stamp = `${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}`;
    return `<article${p.ad ? ' class="ad"' : ''}><div class="who">${esc(p.speaker || '说话人未确认')} · ${stamp}${p.ad ? ' · 广告' : ''}</div><p class="zh">${esc(p.zh)}</p><p class="en" lang="en">${esc(p.en)}</p></article>`;
  }).join('\n');
  return `<section id="s${i+1}"><h2>${String(i+1).padStart(2,'0')} ${esc(section.title)}</h2>${paragraphs}</section>`;
}).join('\n');
if (cursor !== segments.length) throw new Error('来源字幕未完整覆盖');
const template = await readFile(new URL('../assets/template.html', import.meta.url), 'utf8');
const values = {ORIGINAL_TITLE:esc(episode.original_title), TITLE:esc(episode.title), URL:esc(source.url), BODY:body,
  TOC:episode.sections.map((s,i)=>`<a href="#s${i+1}">${esc(s.title)}</a>`).join(''),
  NOTES:esc((episode.notes || []).join('；'))};
const html = template.replace(/\{\{(TITLE|ORIGINAL_TITLE|URL|BODY|TOC|NOTES)\}\}/g, (_, key)=>values[key]);
await writeFile(output, html, {encoding:'utf8', flag:'wx'});
console.log(`PASS：${cursor} 段字幕完整覆盖，英文一致；输出 ${output}`);
