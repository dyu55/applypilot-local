/* ApplyPilot Local: framework-free UI, shipped inside the Python package. */
"use strict";

const $ = (query, root = document) => root.querySelector(query);
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const split = value => String(value || "").split(",").map(x => x.trim()).filter(Boolean);
const token = $('meta[name="workspace-token"]').content;
let state = null;
let currentView = "overview";
let toastTimer;
let jobFilter = "";
let statusFilter = "All statuses";

async function api(path, options = {}) {
  const headers = {"X-Workspace-Token": token, ...(options.headers || {})};
  if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
  const response = await fetch(`/api/${path}`, {...options, headers});
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(typeof data.detail === "string" ? data.detail : "Check the required fields and try again.");
  }
  return response.json();
}

function toast(text, error = false) {
  clearTimeout(toastTimer);
  const box = $("#toast");
  box.textContent = text;
  box.classList.toggle("error", error);
  box.hidden = false;
  toastTimer = setTimeout(() => { box.hidden = true; }, error ? 9000 : 5000);
}

async function reload() {
  state = await api("state");
  $("#account-name").textContent = state.profile.name || "Your workspace";
  $("#profile-id").textContent = `Profile: ${state.profile_id}`;
  $("#avatar").textContent = state.profile.name ? state.profile.name.split(" ").map(x => x[0]).slice(0, 2).join("") : "AP";
  $("#nav-count").textContent = state.jobs.filter(j => j.status === "Pending").length;
  $("#version").textContent = `v${state.version}`;
  render();
}

function heading(title, description, actions = "", eyebrow = "YOUR NEXT CHAPTER") {
  return `<div class="page-heading"><div><p class="eyebrow">${eyebrow}</p><h1>${esc(title)}</h1><p class="description">${esc(description)}</p></div><div class="actions">${actions}</div></div>`;
}
const button = (action, text, primary = false, extra = "") => `<button data-action="${action}" class="${primary ? "primary" : ""}" ${extra}>${text}</button>`;
const badge = status => `<span class="status ${esc(status.replaceAll(" ", "-"))}">${esc(status)}</span>`;
const fit = value => `<span class="fit ${esc(value)}">${esc(value)} fit</span>`;
const empty = (title, description, actions) => `<div class="empty"><div class="empty-icon">&#9671;</div><h2>${esc(title)}</h2><p>${esc(description)}</p><div class="actions">${actions}</div></div>`;
const modalHead = (title, description = "") => `<div class="dialog-heading"><div><h2 id="modal-title">${esc(title)}</h2><p>${esc(description)}</p></div><button class="icon-button" data-action="close" aria-label="Close dialog">&times;</button></div>`;

function jobTable(jobs, limit = 1000) {
  if (!jobs.length) return empty("A fresh start for your search", "Import a few opportunities or connect a public job source to get started.", button("import", "+ Import jobs", true));
  return `<div class="table-wrap"><table><thead><tr><th>OPPORTUNITY</th><th class="location-column">LOCATION</th><th class="fit-column">MATCH</th><th>STATUS</th><th></th></tr></thead><tbody>${jobs.slice(0, limit).map((job, index) => `<tr class="job-row" tabindex="0" data-action="job" data-id="${esc(job.id)}" aria-label="View ${esc(job.title)} at ${esc(job.company)}"><td><div class="job-cell"><span class="company-icon tone-${index % 4}">${esc(job.company.slice(0, 1))}</span><div><div class="job-title">${esc(job.title)}</div><div class="job-company">${esc(job.company)}</div></div></div></td><td class="location-cell location-column">${esc(job.location || "Not specified")}</td><td class="fit-column">${fit(job.assessment.fit)}</td><td>${badge(job.status)}</td><td class="muted">&#8599;</td></tr>`).join("")}</tbody></table></div>`;
}

function overview() {
  const jobs = state.jobs;
  const ready = jobs.filter(j => j.material).length;
  const pending = jobs.filter(j => j.status === "Pending");
  const needed = jobs.filter(j => j.status === "Needs user").length + state.questions.filter(q => !q.resolved).length;
  const counts = [
    ["Opportunities", jobs.length, "Across your connected sources", "&#9671;"],
    ["Materials ready", ready, "Reviewed source facts preserved", "&#9633;"],
    ["Submitted", jobs.filter(j => j.status === "Submitted").length, "With a recorded confirmation", "&#8599;"],
    ["Needs your input", needed, "A small step to keep moving", "&#9716;"]
  ];
  const name = state.profile.name ? `, ${state.profile.name.split(" ")[0]}` : "";
  let html = heading(`Welcome back${name}.`, "A clear view of your search. A little closer to what comes next.", button("import", "+ Import jobs") + button("collect", "Collect opportunities &#8599;", true));
  if (!state.profile.name && !jobs.length) html += `<div class="welcome"><p class="eyebrow">MAKE YOURSELF AT HOME</p><h2>Your career. Your own direction.</h2><p>Bring your resume, set your preferences, and build a search that fits you. Or explore with fictional sample data first.</p><div class="actions"><a class="button primary" href="#settings">Set up my workspace &#8594;</a>${button("demo", "Explore the demo")}</div></div>`;
  html += `<div class="stats">${counts.map(([label, number, caption, symbol]) => `<div class="stat"><span class="stat-label">${label}</span><span class="stat-symbol">${symbol}</span><div class="stat-number">${number}</div><div class="stat-caption">${caption}</div></div>`).join("")}</div>`;
  const list = [...pending, ...jobs.filter(j => j.status !== "Pending")];
  html += `<div class="dashboard-grid"><div class="stack"><section class="panel"><div class="panel-head"><div><h2>Your opportunities</h2><p>Thoughtfully screened for your next move.</p></div><a href="#opportunities" class="text-button">View all &#8594;</a></div>${jobTable(list, 5)}<div class="table-footer"><span>${jobs.length ? `Showing ${Math.min(jobs.length, 5)} of ${jobs.length} opportunities` : "Your next opportunity belongs here"}</span><span>Updated locally</span></div></section><div class="note"><span>&#9679;</span> You stay in control. Materials are drafts; applications need a recorded confirmation.</div></div><div class="stack"><section class="focus-panel"><div class="focus-mark">&#10035;</div><p class="eyebrow">ONE STEP AT A TIME</p><h2>${pending.length ? "Make your next move." : "Build a search that fits."}</h2><p>${pending.length ? `${pending.length} opportunities match your current rules. Choose one, review the details, and prepare your materials.` : "Start with your strengths and preferences. The right opportunities begin with a little clarity."}</p><a class="button small" href="#${pending.length ? "opportunities" : "settings"}">${pending.length ? "Explore your matches" : "Set your preferences"} &#8594;</a></section><section class="panel"><div class="panel-head"><h2>Your foundation</h2></div><div class="panel-body"><ul class="checklist">${[[!!state.profile.name,"Create your profile"],[state.profile.target_roles.length > 0,"Set your career direction"],[state.resumes.length > 0,"Bring your resume"],[jobs.length > 0,"Find your first opportunities"]].map(([done,text]) => `<li><span class="check ${done ? "done" : ""}">${done ? "&#10003;" : ""}</span>${text}</li>`).join("")}</ul></div></section></div></div>`;
  return html;
}

function opportunities() {
  return heading("Room for your next move.", "Explore opportunities, understand the match, and keep every decision in one place.", button("export-csv", "Export CSV") + button("import", "+ Import jobs", true), "OPPORTUNITIES") + `<div class="toolbar"><input id="job-search" class="search-input" type="search" placeholder="Search roles, companies, or locations..." aria-label="Search opportunities" value="${esc(jobFilter)}"><select id="status-filter" aria-label="Filter status">${["All statuses","Pending","Needs user","Submitted","Skipped","Blocked"].map(value => `<option ${value === statusFilter ? "selected" : ""}>${value}</option>`).join("")}</select>${button("collect", "Collect from sources &#8599;")}</div><section class="panel" id="job-results">${filteredJobs()}</section>`;
}

function filteredJobs() {
  const query = jobFilter.toLowerCase();
  const jobs = state.jobs.filter(job => (statusFilter === "All statuses" || job.status === statusFilter) && `${job.title} ${job.company} ${job.location}`.toLowerCase().includes(query));
  return jobs.length ? jobTable(jobs) + `<div class="table-footer">${jobs.length} opportunities</div>` : empty("No opportunities in this view", "Try another search or import a new role to review.", button("import", "+ Import jobs"));
}

function resumes() {
  return heading("Your experience, well told.", "Keep your original resume and role-specific versions together. Every generated fact comes from your source.", button("resume", "+ Add a resume", true), "YOUR MATERIALS") + (state.resumes.length ? `<div class="resume-grid">${state.resumes.map(resume => `<section class="panel resume-card"><div class="resume-art"><div class="mini-page"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div></div><h2>${esc(resume.label)}</h2><p class="muted">${esc(resume.source_name)} &middot; ${resume.text.split(/\s+/).length} words</p><div>${resume.roles.map(role => `<span class="tag">${esc(role)}</span>`).join("") || '<span class="tag">General resume</span>'}</div><div class="form-actions"><button class="small" data-action="preview" data-id="${esc(resume.id)}">Review source &#8594;</button></div></section>`).join("")}</div>` : `<section class="panel">${empty("Bring your story", "Upload a PDF, DOCX, Markdown, or text resume. You can also paste an editable version.", button("resume", "+ Add your first resume", true))}</section>`) + '<p class="note">Original versions are preserved. Tailoring reorders existing bullets without adding experience or claims.</p>';
}

function answers() {
  return heading("Answer once. Move forward.", "Keep confirmed answers within their proper scope. A draft never becomes a personal fact automatically.", button("question", "+ Add a question", true), "ANSWER BANK") + (state.questions.length ? state.questions.map(q => `<section class="panel question-card"><div class="actions"><h3>${esc(q.text)}</h3>${q.resolved ? '<span class="tag">Confirmed</span>' : '<span class="status Needs-user">Needs your input</span>'}</div><p class="meta">Scope: ${esc(q.scope || "General")} &middot; ${q.jobs.length} linked opportunities</p>${q.answer ? `<div class="answer-text">${esc(q.answer.text)}</div><p class="help">${q.answer.source === "resume_based_draft" ? "Resume-based draft; review before using." : "Confirmed by you. Reuse only for an equivalent question in this scope."}</p>` : ""}<div class="form-actions"><button class="small" data-action="answer" data-id="${esc(q.key)}">${q.resolved ? "Update answer" : "Add an answer"} &#8594;</button></div></section>`).join("") : `<section class="panel">${empty("Keep the little details together", "Add a question when a form needs information you have not confirmed. Repeated questions in the same scope stay together.", button("question", "+ Add a question", true))}</section>`);
}

const input = (name, label, value = "", placeholder = "", extra = "") => `<div><label for="${name}">${label}</label><input id="${name}" name="${name}" value="${esc(value)}" placeholder="${placeholder}" ${extra}></div>`;
function settings() {
  const p = state.profile, r = p.rules, m = p.model;
  const sponsorship = p.facts.needs_sponsorship;
  return heading("A search shaped around you.", "Your preferences are yours to define. Unknown personal information stays unknown.", "", "WORKSPACE SETTINGS") + `<form id="settings-form"><section class="panel form-card"><div class="section-title"><span class="section-number">01</span><div><h2>The basics</h2><p>A short introduction to your next chapter.</p></div></div><div class="form-grid">${input("name","Your name",p.name,"Your preferred name")}${input("email","Email",p.email,"you@example.com",'type="email"')}${input("location","Current location",p.location,"City, country")}${input("roles","Target roles",p.target_roles.join(", "),"Product Designer, UX Researcher")}${input("skills","Your skills",p.skills.join(", "),"Research, project management, design")}${input("locations","Preferred locations",r.locations.join(", "),"City or region; leave blank for any")}</div><p class="help">Separate multiple roles, skills, or locations with commas. Role matching uses phrases in job titles.</p></section><section class="panel form-card"><div class="section-title"><span class="section-number">02</span><div><h2>Your ground rules</h2><p>Clear preferences make room for the right opportunities.</p></div></div><div class="form-grid">${input("minimum_salary","Minimum acceptable salary ceiling",r.minimum_salary ?? "","Optional",'type="number" min="0"')}${input("salary_currency","Salary currency",r.salary_currency,"USD, EUR, GBP",'maxlength="3"')}<div><label for="salary_period">Salary period</label><select id="salary_period" name="salary_period">${["year","month","hour"].map(v => `<option ${v===r.salary_period?"selected":""}>${v}</option>`).join("")}</select></div><div><label for="unknown_salary">Undisclosed salary</label><select id="unknown_salary" name="unknown_salary">${["allow","review","skip"].map(v => `<option ${v===r.unknown_salary?"selected":""}>${v}</option>`).join("")}</select></div>${input("excluded_titles","Excluded title phrases",r.excluded_titles.join(", "),"Director, Intern")}${input("excluded_companies","Excluded companies",r.excluded_companies.join(", "),"Optional")}${input("max_age_days","Maximum posting age in days",r.max_age_days ?? "","Any age",'type="number" min="1"')}<div><label for="sponsorship">Do you need employer sponsorship?</label><select id="sponsorship" name="sponsorship"><option value="unknown">Not confirmed</option><option value="yes" ${sponsorship?.value === true ? "selected" : ""}>Yes, in the country below</option><option value="no" ${sponsorship?.value === false ? "selected" : ""}>No, in the country below</option></select></div>${input("sponsorship_country","Country for this sponsorship answer",sponsorship?.scope || "","Country code, for example US or GB")}</div><label class="checkbox-label"><input type="checkbox" name="allow_remote" ${r.allow_remote?"checked":""}> Include remote opportunities</label><p class="help">Currencies and salary periods are compared as published. No exchange rates or annualization are assumed. Remote does not imply eligibility from every country.</p></section><section class="panel form-card"><div class="section-title"><span class="section-number">03</span><div><h2>Where to look</h2><p>Connect public boards or a search provider. Collection is read-only.</p></div></div><div id="source-list">${p.sources.map(sourceRow).join("")}</div>${button("add-source","+ Add a source")}<p class="help">Greenhouse and Lever need an employer board identifier. Remote OK is a public feed. Adzuna uses a country code, search query, and ADZUNA_APP_ID / ADZUNA_APP_KEY environment variables. Sources may apply limits and terms.</p></section><section class="panel form-card"><div class="section-title"><span class="section-number">04</span><div><h2>Optional model assistance</h2><p>Your search works without a model. Enable it only when you want assisted bullet ordering.</p></div></div><label class="checkbox-label"><input type="checkbox" name="model_enabled" ${m.enabled?"checked":""}> Send existing resume bullets and a job excerpt to my configured model</label><div class="form-grid">${input("model_base_url","API base URL",m.base_url,"http://127.0.0.1:11434/v1")}${input("model_name","Model name",m.model,"Your installed or hosted model")}${input("model_key_env","API key environment variable",m.api_key_env,"APPLYPILOT_MODEL_API_KEY")}${input("model_calls","Maximum model calls per material run",m.max_calls_per_run,"3",'type="number" min="1" max="20"')}</div><p class="help">Hosted endpoints require HTTPS and a key set in your shell. Localhost HTTP endpoints are supported. Calls may incur provider charges. The model can reorder existing bullets; it cannot add resume text. Keys are never saved in this form.</p></section><div class="form-actions"><button type="submit" class="primary">Save preferences &#10003;</button></div></form><section class="panel form-card"><h2>Recent collection runs</h2>${state.runs.length ? state.runs.slice(0,5).map(run => `<div class="run-item"><strong>${run.data.imported} imported</strong> &middot; ${run.data.duplicates} duplicates &middot; ${run.data.sources.filter(s=>s.error).length} source issues<small>${esc(new Date(run.created_at).toLocaleString())}</small></div>`).join("") : '<p class="help">Source outcomes will appear here after a collection run.</p>'}</section>`;
}

function sourceRow(source = {}) {
  return `<div class="source-row"><select class="source-kind" aria-label="Source type">${["greenhouse","lever","remoteok","adzuna"].map(kind => `<option ${kind === source.kind ? "selected" : ""}>${kind}</option>`).join("")}</select><input class="source-board" aria-label="Board identifier" placeholder="Board identifier" value="${esc(source.board || "")}"><input class="source-query" aria-label="Search query" placeholder="Search query (optional)" value="${esc(source.query || "")}"><input class="source-region" aria-label="Source region" placeholder="Country: us / gb / eu" value="${esc(source.region || "us")}"><label class="checkbox-label"><input class="source-enabled" type="checkbox" ${source.enabled !== false ? "checked" : ""}> Enabled</label><button type="button" data-action="remove-source">Remove</button></div>`;
}

function render() {
  const views = {overview, opportunities, resumes, answers, settings};
  currentView = location.hash.slice(1) in views ? location.hash.slice(1) : "overview";
  $("#page-name").textContent = {overview:"Overview",opportunities:"Opportunities",resumes:"Resumes",answers:"Answer bank",settings:"Settings"}[currentView];
  document.querySelectorAll("[data-view]").forEach(el => el.classList.toggle("active", el.dataset.view === currentView));
  $("#content").innerHTML = views[currentView]();
  document.querySelectorAll('#settings-form button[data-action]').forEach(el=>el.type="button");
}

function open(html) {
  const modal = $("#modal");
  $("#modal-content").innerHTML = html;
  if (!modal.open) modal.showModal();
}
function importModal(mode = "manual") {
  let body;
  if (mode === "csv") body = `<form id="csv-form"><label for="csv-file">Choose a CSV file</label><input type="file" id="csv-file" accept=".csv" required><p class="help">Required columns: title, company, url. Optional: location, description, salary_min, salary_max, currency, period, remote, country, source_id.</p><div class="form-actions"><button class="primary">Import and screen</button></div></form>`;
  else if (mode === "url") body = `<form id="url-form">${input("url","Public job URL","","https://careers.example.com/job/123",'type="url" required')}<p class="help">Reads structured JobPosting data. If the website does not expose it, use manual entry. No application is started.</p><div class="form-actions"><button class="primary">Read posting</button></div></form>`;
  else body = `<form id="job-form"><div class="form-grid">${input("title","Job title","","Role title",'required')}${input("company","Company","","Employer name",'required')}${input("url","Job URL","","https://example.com/jobs/123",'type="url" required')}${input("location","Location","","City, country")}${input("salary_max","Published salary ceiling","","Optional",'type="number" min="0"')}${input("currency","Currency","","USD, EUR, GBP")}<div><label for="period">Salary period</label><select name="period" id="period"><option value="">Not specified</option><option>year</option><option>month</option><option>hour</option></select></div><div><label for="country">Country code</label><input id="country" name="country" placeholder="US, GB, CA"></div><div class="span-2"><label for="description">Job description</label><textarea name="description" id="description" placeholder="Paste the job description..."></textarea></div></div><label class="checkbox-label"><input name="remote" type="checkbox"> Remote role (check employer location restrictions)</label><div class="form-actions"><button class="primary">Add and screen opportunity</button></div></form>`;
  open(modalHead("Make room for an opportunity.","Add a role to your private workspace.") + `<div class="dialog-tabs">${[["manual","Enter details"],["url","From a URL"],["csv","Import CSV"]].map(([id,text]) => `<button class="${id===mode?"active":""}" data-action="import-tab" data-id="${id}">${text}</button>`).join("")}</div>` + body);
}

function resumeModal() {
  open(modalHead("Bring your experience.", "Original wording and facts stay in your private workspace.") + `<form id="resume-form"><div class="form-grid">${input("label","Version name","","General resume",'required')}${input("resume_roles","Use for these roles","","Designer, Researcher")}</div><div class="detail-section"><label for="resume-file">Upload a resume</label><input type="file" id="resume-file" accept=".pdf,.docx,.md,.txt"><p class="help">PDF, DOCX, Markdown, or plain text. Up to 5 MB. Extracted text should be reviewed before generating materials.</p></div><div class="detail-section"><label for="resume-text">Or paste an editable resume</label><textarea id="resume-text" rows="10" placeholder="Your name, experience, education, and skills..."></textarea><p class="help">Use headings and one-line bullet points. Add at least 40 words of substantive experience.</p></div><div class="form-actions"><button type="submit" class="primary">Save resume version</button></div></form>`);
}

function jobModal(id) {
  const job = state.jobs.find(item=>item.id===id);
  if (!job) return;
  const amount = job.salary_max ? `${job.currency} ${Number(job.salary_max).toLocaleString()} / ${job.period || "unspecified period"}` : "Salary not disclosed";
  const sourceLink = job.source === "remoteok" ? '<a href="https://remoteok.com" target="_blank" rel="noopener">Remote OK</a>' : esc(job.source);
  open(modalHead(job.title,`${job.company} · ${job.location || "Location not specified"}`) + `<div class="detail-meta">${badge(job.status)}${fit(job.assessment.fit)}<span class="tag">${esc(amount)}</span><span class="tag">${esc(job.availability)}</span></div><div class="actions"><a class="button primary" href="${esc(job.url)}" target="_blank" rel="noopener noreferrer">Open original posting &#8599;</a><button data-action="generate" data-id="${esc(id)}">${job.material?"Regenerate materials":"Prepare materials"}</button><button data-action="job-question" data-id="${esc(id)}">Add question</button></div><p class="help">Source: ${sourceLink}. ${esc(job.availability_evidence || "Availability is unverified. Review the employer posting before applying.")}</p>${job.material ? `<div class="material-ready"><strong>Materials ready for your review</strong><p>${job.material.quality.pages} pages &middot; ${job.material.quality.words} words &middot; Source text verified. Your application status is unchanged.</p><div class="actions">${["resume.pdf","resume.md","preparation.md"].map(file=>`<button class="small" data-action="download" data-id="${esc(id)}" data-file="${file}">${file === "resume.pdf" ? "Download PDF" : file === "resume.md" ? "Resume source" : "Preparation notes"}</button>`).join("")}</div>${job.material.warnings.map(w=>`<p class="help">${esc(w)}</p>`).join("")}</div>` : ""}<section class="detail-section"><h3>Why this opportunity is here</h3><ul class="reason-list">${job.assessment.reasons.map(reason=>`<li>${esc(reason)}</li>`).join("")}</ul><div class="detail-meta">${job.assessment.matched_skills.map(skill=>`<span class="tag">${esc(skill)}</span>`).join("")}</div></section><section class="detail-section"><h3>About the role</h3><div class="job-description">${esc(job.description || "No description imported. Read the original posting for details.")}</div></section><section class="detail-section"><h3>Record your next step</h3><p>Submitted requires a confirmation reference. A user-reported receipt is recorded as your report, not an automated verification.</p><form id="status-form" class="status-form" data-id="${esc(id)}"><div><label for="status">Application status</label><select id="status" name="status">${["Pending","Needs user","Blocked","Skipped","Submitted"].map(value=>`<option ${job.status===value?"selected":""}>${value}</option>`).join("")}</select></div>${input("evidence","Confirmation reference or note","","Required for Submitted; no passwords or codes")}<button type="submit">Save status</button></form></section>`);
}

function questionModal(jobId = "") {
  open(modalHead("Keep a question for later.", "Equivalent wording in the same scope is stored once.") + `<form id="question-form" data-job="${esc(jobId)}"><label for="question-text">Question</label><textarea id="question-text" required placeholder="The question exactly as the form asks it..."></textarea><div class="detail-section">${input("scope","Scope","","Country, company, or relevant time period")}</div><div class="form-actions"><button class="primary">Save question</button></div></form>`);
}

async function download(path, name) {
  const response = await fetch(`/api/${path}`, {headers:{"X-Workspace-Token":token}});
  if (!response.ok) throw new Error("The file could not be downloaded. Try generating materials again.");
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url; link.download = name; link.click();
  setTimeout(()=>URL.revokeObjectURL(url), 3000);
}

document.addEventListener("click", async event => {
  const target = event.target.closest("[data-action]");
  if (!target) return;
  event.preventDefault();
  const action = target.dataset.action, id = target.dataset.id;
  target.disabled = true;
  try {
    if (action === "close") $("#modal").close();
    else if (action === "import") importModal();
    else if (action === "import-tab") importModal(id);
    else if (action === "resume") resumeModal();
    else if (action === "job") jobModal(id);
    else if (action === "question") questionModal();
    else if (action === "job-question") questionModal(id);
    else if (action === "add-source") $("#source-list").insertAdjacentHTML("beforeend", sourceRow());
    else if (action === "remove-source") target.closest(".source-row").remove();
    else if (action === "demo") { await api("demo",{method:"POST"}); await reload(); toast("Fictional demo loaded. No real applications were made."); }
    else if (action === "collect") {
      target.textContent = "Collecting...";
      const result = await api("collect",{method:"POST"}); await reload();
      const failed = result.sources.filter(s=>s.error).length;
      toast(`${result.imported} opportunities added, ${result.duplicates} duplicates skipped.${failed ? ` ${failed} sources need attention; see Settings.` : ""}`, failed > 0);
    }
    else if (action === "generate") { target.textContent="Preparing..."; await api(`jobs/${id}/materials`,{method:"POST",body:JSON.stringify({})}); await reload(); jobModal(id); toast("Materials prepared. Review the PDF before applying."); }
    else if (action === "download") await download(`jobs/${id}/materials/${target.dataset.file}`,target.dataset.file);
    else if (action === "export-csv") await download("export/csv","applications.csv");
    else if (action === "preview") { const resume=state.resumes.find(r=>r.id===id); open(modalHead(resume.label,"Original source text")+`<pre class="preview-text">${esc(resume.text)}</pre>`); }
    else if (action === "answer") {
      const q=state.questions.find(q=>q.key===id);
      open(modalHead("An answer you can come back to.",q.text)+`<form id="answer-form" data-id="${esc(id)}"><label for="answer-text">Your confirmed answer</label><textarea id="answer-text" required rows="6">${esc(q.answer?.text||"")}</textarea><p class="help">Scope: ${esc(q.scope||"General")}. Save only information you have confirmed. Do not include passwords, verification codes, or private documents.</p><div class="form-actions"><button class="primary">Save confirmed answer</button></div></form>`);
    }
  } catch (error) { toast(error.message,true); }
  finally { target.disabled=false; if(action==="collect" && target.isConnected) target.textContent="Collect opportunities"; if(action==="generate" && target.isConnected) target.textContent="Prepare materials"; }
});

document.addEventListener("submit", async event => {
  const form=event.target;
  if(!form.id) return;
  event.preventDefault();
  const submit=$('button[type="submit"],button:not([type])',form);
  if(submit) submit.disabled=true;
  try {
    const f=new FormData(form);
    if(form.id === "settings-form") {
      const profile=structuredClone(state.profile);
      Object.assign(profile,{name:f.get("name"),email:f.get("email"),location:f.get("location"),target_roles:split(f.get("roles")),skills:split(f.get("skills"))});
      Object.assign(profile.rules,{locations:split(f.get("locations")),minimum_salary:f.get("minimum_salary")===""?null:Number(f.get("minimum_salary")),salary_currency:String(f.get("salary_currency")).toUpperCase(),salary_period:f.get("salary_period"),unknown_salary:f.get("unknown_salary"),excluded_titles:split(f.get("excluded_titles")),excluded_companies:split(f.get("excluded_companies")),max_age_days:f.get("max_age_days")===""?null:Number(f.get("max_age_days")),allow_remote:f.has("allow_remote")});
      if(f.get("sponsorship") === "unknown") delete profile.facts.needs_sponsorship;
      else {
        if(!String(f.get("sponsorship_country")).trim()) throw new Error("Add a country scope for your sponsorship answer.");
        profile.facts.needs_sponsorship={value:f.get("sponsorship")==="yes",scope:String(f.get("sponsorship_country")).toUpperCase(),source:"user",confirmed_at:new Date().toISOString()};
      }
      profile.sources=Array.from(document.querySelectorAll(".source-row")).map(row=>({kind:$(".source-kind",row).value,board:$(".source-board",row).value.trim(),query:$(".source-query",row).value.trim(),region:$(".source-region",row).value.trim(),enabled:$(".source-enabled",row).checked}));
      Object.assign(profile.model,{enabled:f.has("model_enabled"),base_url:f.get("model_base_url"),model:f.get("model_name"),api_key_env:f.get("model_key_env"),max_calls_per_run:Number(f.get("model_calls"))});
      await api("profile",{method:"PUT",body:JSON.stringify(profile)});await reload();toast("Preferences saved. Existing opportunities have been screened again.");return;
    }
    if(form.id === "job-form") {
      const data=Object.fromEntries(f);data.remote=f.has("remote");data.salary_max=data.salary_max===""?null:Number(data.salary_max);
      await api("jobs",{method:"POST",body:JSON.stringify(data)});
    } else if(form.id === "csv-form") {
      const file=$("#csv-file").files[0];if(!file)throw new Error("Choose a CSV file.");
      if(file.size>3_000_000)throw new Error("CSV files must be smaller than 3 MB.");
      const result=await api("import/csv",{method:"POST",body:JSON.stringify({text:await file.text()})});toast(`${result.imported} added, ${result.duplicates} duplicates skipped.`);
    } else if(form.id === "url-form") await api("import/url",{method:"POST",body:JSON.stringify({url:f.get("url")})});
    else if(form.id === "resume-form") {
      const file=$("#resume-file").files[0];
      if(file) {const payload=new FormData();payload.append("file",file);payload.append("label",f.get("label"));payload.append("roles",f.get("resume_roles"));await api("resumes/upload",{method:"POST",body:payload});}
      else await api("resumes",{method:"POST",body:JSON.stringify({label:f.get("label"),roles:split(f.get("resume_roles")),text:$("#resume-text").value})});
      toast("Resume saved. Review the imported source before preparing materials.");
    } else if(form.id === "status-form") {
      await api(`jobs/${form.dataset.id}/status`,{method:"PATCH",body:JSON.stringify({status:f.get("status"),evidence:f.get("evidence"),evidence_type:"user_reported"})});await reload();jobModal(form.dataset.id);toast("Status and evidence recorded.");return;
    } else if(form.id === "question-form") await api("questions",{method:"POST",body:JSON.stringify({text:$("#question-text").value,scope:f.get("scope"),job_id:form.dataset.job||null})});
    else if(form.id === "answer-form") {const q=state.questions.find(q=>q.key===form.dataset.id);await api("answers",{method:"POST",body:JSON.stringify({question:q.text,scope:q.scope,text:$("#answer-text").value,source:"user_confirmed"})});}
    $("#modal").close();await reload();
  }catch(error){toast(error.message,true);}finally{if(submit)submit.disabled=false;}
});

document.addEventListener("input",event=>{if(event.target.id==="job-search"){jobFilter=event.target.value;$("#job-results").innerHTML=filteredJobs();}});
document.addEventListener("change",event=>{if(event.target.id==="status-filter"){statusFilter=event.target.value;$("#job-results").innerHTML=filteredJobs();}});
document.addEventListener("keydown",event=>{if(event.key==="Enter"&&event.target.classList.contains("job-row"))event.target.click();});
$("#modal").addEventListener("click",event=>{if(event.target===$("#modal")){const r=event.target.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)event.target.close();}});
window.addEventListener("hashchange",()=>{if(state)render();});
reload().catch(error=>{$("#content").innerHTML=empty("The workspace could not be opened",error.message,'<a class="button" href="/">Reload workspace</a>');});
