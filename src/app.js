import { SCENE_IDS } from "./scenes.js";
import { validatePage, summary, visibleLength } from "./validate.js";

const SHELF_KEY = "ssg.shelf.v1";
const CURRENT_KEY = "ssg.current.v1";

const app = {
  rules: null,
  scenes: {},
  story: null,     // 正在读的故事
  index: 0,
  demoTimer: null,
};

const view = () => document.getElementById("view");
const topbar = () => document.getElementById("topbar");
const tabbar = () => document.getElementById("tabbar");

const h = (html) => {
  const t = document.createElement("template");
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
};

const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// ---------------- 数据 ----------------
async function boot() {
  app.rules = await fetch("content/rules.json").then((r) => r.json());
  await Promise.all(
    SCENE_IDS.map(async (id) => {
      app.scenes[id] = await fetch(`content/scenes/${id}.json`).then((r) => r.json());
    })
  );
  render();
}

function inject(text, scene, vars) {
  return String(text).replace(/\{(\w+)\}/g, (m, key) => {
    const v = vars && vars[key];
    if (v) return v;
    return (scene.slots[key] && scene.slots[key].default) || m;
  });
}

function buildStory(sceneId, vars, editedFirstPage) {
  const scene = app.scenes[sceneId];
  const pages = scene.pages.map((p, i) => ({
    text: inject(p.text, scene, vars),
    type: p.type,
    img: p.img,
    alt: p.alt,
  }));
  if (editedFirstPage) pages[0].text = editedFirstPage;
  return {
    sceneId,
    vars: vars || {},
    title: inject(scene.title, scene, vars),
    pages,
    imagePool: scene.image_pool,
    durationSec: scene.duration_sec,
    createdAt: Date.now(),
  };
}

function readShelf() {
  try {
    return JSON.parse(localStorage.getItem(SHELF_KEY) || "[]");
  } catch (e) {
    return [];
  }
}

function writeShelf(list) {
  localStorage.setItem(SHELF_KEY, JSON.stringify(list));
}

function saveStory(story) {
  const list = readShelf();
  list.unshift(story);
  writeShelf(list.slice(0, 40));
}

function setCurrent(story) {
  app.story = story;
  app.index = 0;
  sessionStorage.setItem(CURRENT_KEY, JSON.stringify(story));
}

function getCurrent() {
  if (app.story) return app.story;
  try {
    app.story = JSON.parse(sessionStorage.getItem(CURRENT_KEY) || "null");
  } catch (e) {
    app.story = null;
  }
  return app.story;
}

function varsSummary(scene, vars) {
  const parts = [];
  for (const key of ["child", "who", "when", "where"]) {
    if (!scene.slots[key]) continue;
    const v = (vars && vars[key]) || scene.slots[key].default;
    parts.push(v);
  }
  return parts.join(" · ");
}

// ---------------- 路由 ----------------
function currentRoute() {
  const raw = location.hash.replace(/^#\/?/, "").split("?")[0];
  const [name, arg] = raw.split("/");
  return { name: name || "list", arg };
}

function go(hash) {
  if (location.hash === hash) render();
  else location.hash = hash;
}

function render() {
  stopDemo();
  const { name, arg } = currentRoute();
  const v = view();
  v.innerHTML = "";
  let node;
  if (name === "shelf") node = viewShelf();
  else if (name === "custom") node = viewCustom(arg);
  else if (name === "read") node = viewReader(arg);
  else if (name === "demo") node = viewDemo(arg);
  else node = viewList();
  v.appendChild(node);
  renderChrome(name);
}

function renderChrome(route) {
  document.getElementById("view").className =
    route === "read" || route === "demo" ? "reading" : "";
  const tab = tabbar();
  tab.innerHTML = "";
  tab.appendChild(
    h(`<button data-go="#/list" class="${route === "list" || route === "custom" || route === "read" || route === "demo" ? "on" : ""}">
        <span class="ico">📖</span>故事</button>`)
  );
  tab.appendChild(
    h(`<button data-go="#/shelf" class="${route === "shelf" ? "on" : ""}">
        <span class="ico">🗂</span>书架</button>`)
  );
  tab.querySelectorAll("button").forEach((b) =>
    b.addEventListener("click", () => go(b.dataset.go))
  );
  tab.style.display = route === "read" || route === "demo" ? "none" : "flex";
}

function setTopbar(title, { back = null, sub = "" } = {}) {
  const bar = topbar();
  bar.innerHTML = "";
  if (back) {
    const b = h(`<button class="back-btn" aria-label="返回">‹</button>`);
    b.addEventListener("click", () => go(back));
    bar.appendChild(b);
  }
  bar.appendChild(h(`<h1>${esc(title)}</h1>`));
  if (sub) bar.appendChild(h(`<span class="sub">${esc(sub)}</span>`));
}

// ---------------- 列表 ----------------
function viewList() {
  setTopbar("社交故事器", { sub: `${SCENE_IDS.length} 个场景` });
  const wrap = h(`<div></div>`);
  wrap.appendChild(
    h(`<p class="lead">孩子怕的不是医院和学校，是"不知道接下来会发生什么"。<br>选一个场景，填上孩子的小名，六页读完。</p>`)
  );
  for (const id of SCENE_IDS) {
    const scene = app.scenes[id];
    const cover = `${scene.image_pool}/01.webp`;
    const card = h(`<div class="scene-card">
        <div class="thumb"><img src="${cover}" alt="" loading="lazy"></div>
        <div class="meta">
          <div class="name">${esc(scene.name)}</div>
          <div class="desc">${esc(scene.audience)} 岁 · 约 ${Math.round(scene.duration_sec)} 秒 · ${scene.pages.length} 页</div>
        </div>
      </div>`);
    const img = card.querySelector("img");
    img.addEventListener("error", () => {
      img.remove();
      const thumb = card.querySelector(".thumb");
      thumb.classList.add("empty");
      thumb.textContent = "图待出";
    });
    card.addEventListener("click", () => go(`#/custom/${id}`));
    wrap.appendChild(card);
  }
  wrap.appendChild(
    h(`<p class="hint">读完可以存进书架，下次直接翻。</p>`)
  );
  return wrap;
}

// ---------------- 自定义 ----------------
function viewCustom(sceneId) {
  const scene = app.scenes[sceneId] || app.scenes[SCENE_IDS[0]];
  setTopbar(scene.name, { back: "#/list" });

  const wrap = h(`<div></div>`);
  wrap.appendChild(h(`<p class="lead">填四个空，故事就是你家孩子的事。留空用默认值。</p>`));

  const vars = {};
  for (const key of ["child", "who", "when", "where"]) {
    const slot = scene.slots[key];
    if (!slot) continue;
    vars[key] = "";
    const field = h(`<div class="field">
        <label><span>${esc(slot.label)}</span><span>最多 ${slot.max} 字</span></label>
        <input name="${key}" maxlength="${slot.max}" placeholder="${esc(slot.default)}" autocomplete="off">
      </div>`);
    field.querySelector("input").addEventListener("input", updatePreview);
    wrap.appendChild(field);
  }

  const preview = h(`<div class="preview">
      <div class="cap">读起来是这样</div>
      <div class="title"></div>
      <div class="line"></div>
    </div>`);
  wrap.appendChild(preview);

  wrap.appendChild(h(`<p class="hint">第一页想自己改一句？改完会立刻按 R1–R6 检查。</p>`));
  const editField = h(`<div class="field">
      <label><span>第一页（可留空）</span><span>≤ ${app.rules.max_len} 字</span></label>
      <textarea name="edit" placeholder="留空就用模板原句"></textarea>
    </div>`);
  wrap.appendChild(editField);
  const check = h(`<div class="check"></div>`);
  check.style.display = "none";
  wrap.appendChild(check);

  const btn = h(`<button class="btn-primary">开始读</button>`);
  btn.addEventListener("click", () => {
    const values = collect();
    setCurrent(buildStory(scene.id, values.vars, values.edited));
    go("#/read");
  });
  wrap.appendChild(btn);

  const saveBtn = h(`<button class="btn-ghost">存进书架</button>`);
  saveBtn.addEventListener("click", () => {
    const values = collect();
    const story = buildStory(scene.id, values.vars, values.edited);
    saveStory(story);
    saveBtn.textContent = "已存进书架 ✓";
    setTimeout(() => (saveBtn.textContent = "存进书架"), 1400);
  });
  wrap.appendChild(saveBtn);

  function collect() {
    const values = {};
    wrap.querySelectorAll("input[name]").forEach((i) => {
      const val = i.value.trim();
      if (val) values[i.name] = val;
    });
    let edited = editField.querySelector("textarea").value.trim();
    if (edited) {
      const issues = validatePage(edited, scene.pages[0].type, app.rules);
      if (issues.some((i) => i.level === "error")) edited = "";
    }
    return { vars: values, edited };
  }

  function updatePreview() {
    const values = collect();
    const story = buildStory(scene.id, values.vars, values.edited);
    preview.querySelector(".title").textContent = story.title;
    preview.querySelector(".line").textContent = story.pages[0].text;
  }

  editField.querySelector("textarea").addEventListener("input", (e) => {
    const text = e.target.value.trim();
    if (!text) {
      check.style.display = "none";
      updatePreview();
      return;
    }
    const issues = validatePage(text, scene.pages[0].type, app.rules);
    const s = summary(issues);
    check.style.display = "block";
    check.className = "check " + (s.ok ? "ok" : "bad");
    check.innerHTML =
      `<strong>${esc(s.text)}</strong>` +
      (issues.length
        ? `<ul>${issues.map((i) => `<li>${esc(i.msg)}</li>`).join("")}</ul>`
        : "");
    updatePreview();
  });

  setTimeout(updatePreview, 0);
  return wrap;
}

// ---------------- 阅读器 ----------------
function viewReader(sceneId) {
  let story = getCurrent();
  // 直接带场景 id 进来（演示/刷新）时，用默认变量现搭一个
  if ((!story || (sceneId && story.sceneId !== sceneId)) && sceneId) {
    setCurrent(buildStory(sceneId, {}));
    story = app.story;
  }
  if (!story) {
    setTopbar("没有故事", { back: "#/list" });
    return h(`<div class="empty">还没有打开过故事。<br>先从列表里选一个。</div>`);
  }
  const scene = app.scenes[story.sceneId];
  setTopbar(scene.name, { back: `#/custom/${story.sceneId}` });

  // 支持 #/read/kindergarten?p=4 直接翻到某页（截图、答辩跳页用）
  const pm = location.hash.match(/[?&]p=(\d+)/);
  if (pm) {
    const n = parseInt(pm[1], 10) - 1;
    app.index = Math.min(Math.max(0, n), story.pages.length - 1);
  }

  const wrap = h(`<div></div>`);
  const title = h(`<p class="reader-title">${esc(story.title)}<small>${esc(varsSummary(scene, story.vars))}</small></p>`);
  wrap.appendChild(title);

  const stage = h(`<div class="stage"></div>`);
  wrap.appendChild(stage);

  const foot = h(`<div class="reader-foot">
      <div class="dots"></div>
      <button class="nav-btn prev" aria-label="上一页">‹</button>
      <button class="nav-btn next" aria-label="下一页">›</button>
    </div>`);
  wrap.appendChild(foot);

  const demoBtn = h(`<button class="btn-ghost">用演示模式看一遍（自动翻页）</button>`);
  demoBtn.addEventListener("click", () => go(`#/demo/${story.sceneId}`));
  wrap.appendChild(demoBtn);

  function paint() {
    const page = story.pages[app.index];
    stage.innerHTML = "";
    const src = `${story.imagePool}/${page.img}`;
    const img = new Image();
    img.alt = page.alt || "";
    img.src = src;
    img.onerror = () => {
      stage.innerHTML = "";
      stage.appendChild(h(`<div class="placeholder">${esc(page.alt || "这一页的图还没生成")}</div>`));
      stage.appendChild(textNode(page.text));
    };
    img.onload = () => {
      stage.appendChild(img);
      stage.appendChild(textNode(page.text));
    };
    if (img.complete && img.naturalWidth) img.onload();

    const dots = foot.querySelector(".dots");
    dots.innerHTML = "";
    story.pages.forEach((_, i) => dots.appendChild(h(`<span class="dot ${i === app.index ? "on" : ""}"></span>`)));
    foot.querySelector(".prev").disabled = app.index === 0;
    foot.querySelector(".next").disabled = app.index === story.pages.length - 1;
  }

  function textNode(text) {
    const len = visibleLength(text);
    const cls = len <= 12 ? "len-s" : len <= 17 ? "len-m" : "len-l";
    return h(`<div class="page-text ${cls}">${esc(text)}</div>`);
  }

  function next() {
    if (app.index < story.pages.length - 1) {
      app.index++;
      paint();
    }
  }
  function prev() {
    if (app.index > 0) {
      app.index--;
      paint();
    }
  }

  foot.querySelector(".next").addEventListener("click", next);
  foot.querySelector(".prev").addEventListener("click", prev);

  stage.addEventListener("click", (e) => {
    const rect = stage.getBoundingClientRect();
    if (e.clientX - rect.left < rect.width / 2) prev();
    else next();
  });

  let touchX = null;
  stage.addEventListener("touchstart", (e) => (touchX = e.touches[0].clientX), { passive: true });
  stage.addEventListener("touchend", (e) => {
    if (touchX === null) return;
    const dx = e.changedTouches[0].clientX - touchX;
    if (Math.abs(dx) > 40) (dx < 0 ? next : prev)();
    touchX = null;
  });

  const onKey = (e) => {
    if (e.key === "ArrowRight") next();
    if (e.key === "ArrowLeft") prev();
    if (e.key === "Escape") go("#/list");
  };
  document.addEventListener("keydown", onKey);
  app.cleanup = () => document.removeEventListener("keydown", onKey);

  paint();
  return wrap;
}

// ---------------- 书架 ----------------
function viewShelf() {
  setTopbar("我的书架", { sub: `${readShelf().length} 个` });
  const wrap = h(`<div></div>`);
  const list = readShelf();
  if (!list.length) {
    wrap.appendChild(h(`<div class="empty">书架还是空的。<br>读一个场景，"存进书架"就会出现在这里。</div>`));
    return wrap;
  }
  list.forEach((story, i) => {
    const scene = app.scenes[story.sceneId];
    const item = h(`<div class="shelf-item">
        <div class="info">
          <div class="t">${esc(story.title)}</div>
          <div class="v">${esc(scene ? varsSummary(scene, story.vars) : "")} · ${new Date(story.createdAt).toLocaleDateString("zh-CN")}</div>
        </div>
        <button class="del">删</button>
      </div>`);
    item.querySelector(".info").addEventListener("click", () => {
      setCurrent(story);
      go("#/read");
    });
    item.querySelector(".del").addEventListener("click", (e) => {
      e.stopPropagation();
      const nextList = readShelf().filter((_, idx) => idx !== i);
      writeShelf(nextList);
      render();
    });
    wrap.appendChild(item);
  });
  return wrap;
}

// ---------------- 演示模式 ----------------
function viewDemo(sceneId) {
  const story = getCurrent() && getCurrent().sceneId === sceneId ? getCurrent() : null;
  const target = story || buildStory(sceneId || SCENE_IDS[0], {});
  if (!story) setCurrent(target);

  setTopbar("演示模式", { back: `#/read`, sub: "自动翻页" });
  const wrap = h(`<div></div>`);
  const progWrap = h(`<div class="demo-progress"><i></i></div>`);
  wrap.appendChild(progWrap);

  const stage = h(`<div class="stage"></div>`);
  wrap.appendChild(stage);

  const reminder = h(`<div class="reminder">
      <div class="card">
        <div class="app">提醒 · 社交故事器</div>
        <div class="t">${esc(target.title)}</div>
        <div class="d">到时间了。点开，一起读六页，大概一分钟。</div>
        <button>打开故事</button>
      </div>
    </div>`);
  wrap.appendChild(reminder);

  const foot = h(`<div class="reader-foot">
      <div class="dots"></div>
      <button class="nav-btn stop">停下</button>
    </div>`);
  wrap.appendChild(foot);

  let index = 0;
  const perPage = Math.max(2200, Math.round((target.durationSec * 1000) / target.pages.length));

  function paint() {
    const page = target.pages[index];
    stage.innerHTML = "";
    const img = new Image();
    img.src = `${target.imagePool}/${page.img}`;
    img.alt = page.alt || "";
    img.onload = () => {
      stage.appendChild(img);
      stage.appendChild(textNode(page.text));
    };
    img.onerror = () => {
      stage.appendChild(h(`<div class="placeholder">${esc(page.alt || "图还没生成")}</div>`));
      stage.appendChild(textNode(page.text));
    };
    if (img.complete && img.naturalWidth) img.onload();

    const dots = foot.querySelector(".dots");
    dots.innerHTML = "";
    target.pages.forEach((_, i) => dots.appendChild(h(`<span class="dot ${i === index ? "on" : ""}"></span>`)));
    progWrap.querySelector("i").style.width = `${((index + 1) / target.pages.length) * 100}%`;
  }

  function textNode(text) {
    const len = visibleLength(text);
    const cls = len <= 12 ? "len-s" : len <= 17 ? "len-m" : "len-l";
    return h(`<div class="page-text ${cls}">${esc(text)}</div>`);
  }

  function start() {
    reminder.remove();
    index = 0;
    paint();
    app.demoTimer = setInterval(() => {
      if (index < target.pages.length - 1) {
        index++;
        paint();
      } else {
        stopDemo();
        finish();
      }
    }, perPage);
  }

  function finish() {
    stage.innerHTML = "";
    progWrap.querySelector("i").style.width = "100%";
    const end = h(`<div class="stage" style="display:flex;align-items:center;justify-content:center;">
        <div class="demo-end">
          <div class="big">读完了。</div>
          <div class="small">刚才那六页，就是${esc(target.vars.who || "妈妈")}下次会讲给孩子的。</div>
          <button class="nav-btn again">再看一遍</button>
        </div>
      </div>`);
    stage.replaceWith(end);
    end.querySelector(".again").addEventListener("click", () => go(`#/demo/${target.sceneId}`));
  }

  reminder.querySelector("button").addEventListener("click", start);  foot.querySelector(".stop").addEventListener("click", () => {
    stopDemo();
    reminder.remove();
    go(`#/read`);
  });

  paint();
  return wrap;
}

function stopDemo() {
  if (app.demoTimer) {
    clearInterval(app.demoTimer);
    app.demoTimer = null;
  }
  if (app.cleanup) {
    app.cleanup();
    app.cleanup = null;
  }
}

window.addEventListener("hashchange", render);
boot().catch((err) => {
  view().appendChild(h(`<div class="empty">加载失败：${esc(err.message)}<br>请通过本地服务器打开（file:// 无法读取 JSON）。</div>`));
});
