// 前端校验：阈值全部来自 content/rules.json，不另写一套（schema.md §4）
// 只做"改一句"时需要的即时反馈，完整机检仍以 check_social_story.py 为准。

export function visibleLength(text) {
  return Array.from(text.replace(/[\s]/g, "")).length;
}

export function validatePage(text, type, rules) {
  const issues = [];
  const raw = (text || "").trim();

  if (!raw) {
    issues.push({ level: "error", msg: "这一页还没有字。" });
    return issues;
  }

  const len = visibleLength(raw);
  if (len > rules.max_len) {
    issues.push({ level: "error", msg: `太长：${len} 字，上限 ${rules.max_len} 字。` });
  }

  for (const w of rules.second_person) {
    if (raw.includes(w)) {
      issues.push({ level: "error", msg: `不能出现第二人称「${w}」，整篇用「我」。` });
    }
  }

  for (const w of rules.banned) {
    if (raw.includes(w)) {
      issues.push({ level: "error", msg: `「${w}」是禁用词，会变成命令而不是故事。` });
    }
  }

  const endsWithSentence = rules.sentence_end.some((p) => raw.endsWith(p));
  if (!endsWithSentence) {
    issues.push({ level: "warn", msg: "句末最好有标点（。！？）。" });
  }

  const ends = rules.sentence_end.filter((p) => raw.endsWith(p)).length;
  if (ends > 1) {
    issues.push({ level: "error", msg: "一页只能有一句。" });
  }

  const concrete = rules.concrete || {};
  const hasTime = (concrete.time || []).some((w) => raw.includes(w));
  const hasAction = (concrete.action || []).some((w) => raw.includes(w));
  const hasPlace = (concrete.place || []).some((w) => raw.includes(w));
  if (!hasTime && !hasAction && !hasPlace) {
    issues.push({ level: "warn", msg: "这句里没有具体的时间、动作或地方，孩子不容易想象。" });
  }

  if (!rules.types.includes(type)) {
    issues.push({ level: "error", msg: `句型 ${type} 不在四种之内。` });
  }

  return issues;
}

export function summary(issues) {
  const errors = issues.filter((i) => i.level === "error").length;
  if (!issues.length) return { ok: true, text: "这句可以通过。" };
  if (!errors) return { ok: true, text: `通过，有 ${issues.length} 条小提醒。` };
  return { ok: false, text: `${errors} 处要改。` };
}
