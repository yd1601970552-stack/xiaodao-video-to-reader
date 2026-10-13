// 维护者使用：node scripts/sync-reader.mjs [--apply]
// 默认只检查；--apply 仅更新本包内置阅读器，不修改用户已安装的阅读器。
import {readFile, writeFile, mkdir, copyFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const root = new URL('../', import.meta.url);
const repo = 'yd1601970552-stack/html-reader-annotator';
async function api(path) {
  const response = await fetch(`https://api.github.com/repos/${repo}/${path}`, {signal:AbortSignal.timeout(20000)});
  if (!response.ok) throw new Error(`GitHub HTTP ${response.status}`);
  return response.json();
}
const commit = (await api('commits/main')).sha;
const manifest = JSON.parse(await readFile(new URL('vendor-manifest.json', root), 'utf8'));
const old = manifest.find(x=>x.repo===repo)?.commit;
if (!process.argv.includes('--apply')) {
  console.log(JSON.stringify({bundled:old,latest:commit,changed:old!==commit,action:'使用 --apply 同步包内版本，不自动更新桌面安装'}));
} else {
  const entries = [];
  const files = [];
  for (const path of ['index.html','LICENSE']) {
    const file = await api(`contents/${path}?ref=${commit}`);
    const data = Buffer.from(file.content, 'base64');
    if (path==='index.html' && (!data.toString('utf8').includes('id="file"') || !data.toString('utf8').includes('id="page"'))) throw new Error('上游结构变化，需要人工检查后适配');
    if (path==='LICENSE' && !data.toString('utf8').includes('MIT License')) throw new Error('许可证变化，需要人工审查');
    files.push({path,data});
    entries.push({repo,commit,path,local:`assets/reader/${path}`,sha256:createHash('sha256').update(data).digest('hex')});
  }
  const backup = new URL(`work/reader-backup-${old}/`, root);
  await mkdir(backup,{recursive:true});
  for (const {path,data} of files) {
    await copyFile(new URL(`assets/reader/${path}`,root),new URL(path,backup));
    await writeFile(new URL(`assets/reader/${path}`,root),data);
  }
  await writeFile(new URL('vendor-manifest.json',root),JSON.stringify([...manifest.filter(x=>x.repo!==repo),...entries],null,2));
  const noticesUrl=new URL('THIRD_PARTY_NOTICES.md',root);
  const notices=await readFile(noticesUrl,'utf8');
  await writeFile(noticesUrl,notices.replace(old,commit));
  console.log(`已同步 ${commit}，旧文件备份在 work；请重新验证阅读器并打包。桌面安装未修改。`);
}
