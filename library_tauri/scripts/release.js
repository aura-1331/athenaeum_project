import fs from "fs";
import path from "path";
import { execSync } from "child_process";

const root = path.resolve(import.meta.dirname, "../..");
const packagePath = path.join(root, "library_tauri", "package.json");
const tauriPath = path.join(root, "library_tauri", "src-tauri", "tauri.conf.json");
const changelogPath = path.join(root, "library_api", "app", "changelog.json");

const type = process.argv[2];
const dryRun = process.argv.includes("--dry-run");

if (!["patch", "minor", "major"].includes(type)) {
  console.error("Usage: npm run release:patch|minor|major [-- --dry-run]");
  process.exit(1);
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8").replace(/^\uFEFF/, ""));
}

function writeJson(file, data) {
  fs.writeFileSync(file, JSON.stringify(data, null, 2) + "\n", "utf8");
}

function git(command) {
  return execSync(command, {
    cwd: root,
    encoding: "utf8",
    stdio: ["pipe", "pipe", "pipe"],
  }).trim();
}

function parseVersion(version) {
  const match = version.match(/^(\d+)\.(\d+)\.(\d+)$/);

  if (!match) {
    throw new Error(`Invalid version: ${version}`);
  }

  return {
    major: Number(match[1]),
    minor: Number(match[2]),
    patch: Number(match[3]),
  };
}

function bumpVersion(version, type) {
  const v = parseVersion(version);

  if (type === "major") {
    return `${v.major + 1}.0.0`;
  }

  if (type === "minor") {
    return `${v.major}.${v.minor + 1}.0`;
  }

  return `${v.major}.${v.minor}.${v.patch + 1}`;
}

function classifyCommit(subject) {
  const text = subject.toLowerCase();

  if (
    /\b(auth|authentication|authorization|csrf|security|session|token|password|permission|audit|ledger|identity)\b/.test(text)
  ) {
    return "Security & Authentication";
  }

  if (
    /\b(feat|feature|add|added|implement|implemented|introduce|introduced|support)\b/.test(text)
  ) {
    return "Features";
  }

  if (
    /\b(fix|fixed|bug|repair|resolve|resolved|correct|correction|patch)\b/.test(text)
  ) {
    return "Bug Fixes";
  }

  if (
    /\b(ui|ux|design|layout|style|visual|frontend|interface|theme)\b/.test(text)
  ) {
    return "UI & UX";
  }

  if (
    /\b(perf|performance|optimiz|speed|memory|stability|crash|reliability)\b/.test(text)
  ) {
    return "Performance & Stability";
  }

  if (
    /\b(build|release|deploy|deployment|workflow|ci|cd|github|node|rust|tauri|pipeline|production|infrastructure)\b/.test(text)
  ) {
    return "Infrastructure & Release";
  }

  if (
    /\b(doc|docs|documentation|readme)\b/.test(text)
  ) {
    return "Documentation";
  }

  return "Changes";
}

function cleanCommitMessage(subject) {
  return subject
    .replace(/^(feat|fix|docs|style|refactor|perf|test|build|ci|chore)(\([^)]+\))?!?:\s*/i, "")
    .replace(/^\[[^\]]+\]\s*/i, "")
    .trim();
}

const pkg = readJson(packagePath);
const tauri = readJson(tauriPath);
const changelog = readJson(changelogPath);

const currentVersion = pkg.version;
const newVersion = bumpVersion(currentVersion, type);
const tag = `v${newVersion}`;

let previousTag;

try {
  previousTag = git("git describe --tags --abbrev=0");
} catch {
  previousTag = null;
}

let commits = [];

if (previousTag) {
  const output = git(
    `git log ${previousTag}..HEAD --pretty=format:%s`
  );

  if (output) {
    commits = output
  .split(/\r?\n/)
  .map(cleanCommitMessage)
  .filter(Boolean)
  .filter(
    (commit) =>
      !/^Update changelog for v\d+\.\d+\.\d+$/i.test(commit)
  );
  }
}

const sections = new Map();

for (const commit of commits) {
  const category = classifyCommit(commit);

  if (!sections.has(category)) {
    sections.set(category, []);
  }

  sections.get(category).push(commit);
}

if (sections.size === 0) {
  sections.set("Changes", [
    "Release preparation and version update"
  ]);
}

const generatedSections = Array.from(sections.entries()).map(
  ([category, notes]) => ({
    category,
    notes,
  })
);

const releaseEntry = {
  version: tag,
  date: new Date().toISOString().slice(0, 10),
  sections: generatedSections,
};

console.log("");
console.log("========================================");
console.log("        ATHENAEUM RELEASE PREVIEW");
console.log("========================================");
console.log("");
console.log(`Current version: ${currentVersion}`);
console.log(`New version:     ${newVersion}`);
console.log(`Tag:             ${tag}`);
console.log(`Previous tag:    ${previousTag ?? "none"}`);
console.log("");

console.log("CHANGELOG");
console.log("----------------------------------------");

for (const section of generatedSections) {
  console.log(`\n${section.category}`);

  for (const note of section.notes) {
    console.log(`  - ${note}`);
  }
}

console.log("");
console.log("----------------------------------------");

if (dryRun) {
  console.log("");
  console.log("DRY RUN");
  console.log("No files changed.");
  console.log("No commit created.");
  console.log("No tag created.");
  console.log("Nothing pushed.");
  process.exit(0);
}

const status = git("git status --porcelain");

if (status) {
  console.error("");
  console.error("ERROR: Working tree is not clean.");
  console.error("");
  console.error(status);
  console.error("");
  console.error("Commit or remove unrelated changes before releasing.");
  process.exit(1);
}

const existingTag = git(`git tag -l ${tag}`);

if (existingTag) {
  console.error(`ERROR: Tag ${tag} already exists.`);
  process.exit(1);
}

console.log("");
console.log("Create this release? [Y/N]");

process.stdin.setEncoding("utf8");

process.stdin.once("data", (answer) => {
  if (answer.trim().toLowerCase() !== "y") {
    console.log("");
    console.log("Release cancelled. No files changed.");
    process.exit(0);
  }

  try {
    pkg.version = newVersion;
    tauri.version = newVersion;

    changelog.unshift(releaseEntry);

    writeJson(packagePath, pkg);
    writeJson(tauriPath, tauri);
    writeJson(changelogPath, changelog);

    git("git add library_tauri/package.json library_tauri/src-tauri/tauri.conf.json library_api/app/changelog.json");

    git(`git commit -m "Release ${tag}"`);
    git(`git tag ${tag}`);
    git("git push origin main");
    git(`git push origin ${tag}`);

    console.log("");
    console.log("========================================");
    console.log("        RELEASE COMPLETE");
    console.log("========================================");
    console.log("");
    console.log(`Released: ${tag}`);
    console.log("");
  } catch (error) {
    console.error("");
    console.error("RELEASE FAILED");
    console.error("");
    console.error(error.message);
    process.exit(1);
  }
});