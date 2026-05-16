#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";

const repoRoot = path.resolve(process.argv[2] || process.cwd());
const anchorDir = path.join(repoRoot, "openspec/orchestrate/source-anchors");

function fail(message) {
  console.error(message);
  process.exit(2);
}

if (!fs.existsSync(anchorDir)) {
  fail(`Missing anchor directory: ${anchorDir}`);
}

const anchorFiles = fs
  .readdirSync(anchorDir)
  .filter((name) => name.endsWith(".md") && name !== "index.md")
  .sort();

if (anchorFiles.length === 0) {
  fail(`No per-document anchor files found in: ${anchorDir}`);
}

const results = [];

for (const fileName of anchorFiles) {
  const anchorPath = path.join(anchorDir, fileName);
  const markdown = fs.readFileSync(anchorPath, "utf8");
  const markdownLines = markdown.split(/\r?\n/);
  const sourceLine = markdownLines.find((line) =>
    /^-?\s*Source Document:\s*`[^`]+`/i.test(line.trim()),
  );

  if (!sourceLine) {
    results.push({
      anchorFile: path.relative(repoRoot, anchorPath),
      sourceDocument: null,
      anchors: 0,
      nonEmptyLines: 0,
      uncoveredNonEmptyLines: 0,
      overlapLines: 0,
      badRanges: 0,
      status: "failed",
      notes: "Missing `Source Document: ` metadata line.",
    });
    continue;
  }

  const sourceDocument = sourceLine.match(/`([^`]+)`/)?.[1];
  const sourcePath = path.join(repoRoot, sourceDocument);
  if (!sourceDocument || !fs.existsSync(sourcePath)) {
    results.push({
      anchorFile: path.relative(repoRoot, anchorPath),
      sourceDocument,
      anchors: 0,
      nonEmptyLines: 0,
      uncoveredNonEmptyLines: 0,
      overlapLines: 0,
      badRanges: 0,
      status: "failed",
      notes: "Source document is missing or cannot be resolved.",
    });
    continue;
  }

  const sourceLines = fs.readFileSync(sourcePath, "utf8").split(/\r?\n/);
  const coverage = Array.from({ length: sourceLines.length + 1 }, () => 0);
  let anchors = 0;
  let badRanges = 0;

  for (const line of markdownLines) {
    if (!line.startsWith("| ")) continue;
    if (line.includes("| Anchor | Lines |")) continue;
    if (line.includes("| --- |")) continue;

    const cells = line
      .split("|")
      .slice(1, -1)
      .map((cell) => cell.trim());
    if (cells.length < 8) continue;

    anchors += 1;
    const ranges = cells[1]
      .split(/<br>|[,;]/)
      .map((part) => part.trim())
      .filter(Boolean);

    for (const range of ranges) {
      const match = range.match(/^L(\d+)(?:-L(\d+))?$/);
      if (!match) {
        badRanges += 1;
        continue;
      }

      const start = Number(match[1]);
      const end = Number(match[2] || match[1]);
      if (start < 1 || end < start || end > sourceLines.length) {
        badRanges += 1;
        continue;
      }

      for (let lineNumber = start; lineNumber <= end; lineNumber += 1) {
        coverage[lineNumber] += 1;
      }
    }
  }

  let nonEmptyLines = 0;
  let uncoveredNonEmptyLines = 0;
  let overlapLines = 0;

  for (let lineNumber = 1; lineNumber <= sourceLines.length; lineNumber += 1) {
    if (sourceLines[lineNumber - 1].trim().length > 0) {
      nonEmptyLines += 1;
      if (coverage[lineNumber] === 0) uncoveredNonEmptyLines += 1;
    }
    if (coverage[lineNumber] > 1) overlapLines += 1;
  }

  results.push({
    anchorFile: path.relative(repoRoot, anchorPath),
    sourceDocument,
    anchors,
    nonEmptyLines,
    uncoveredNonEmptyLines,
    overlapLines,
    badRanges,
    status:
      uncoveredNonEmptyLines === 0 && overlapLines === 0 && badRanges === 0
        ? "passed"
        : "failed",
    notes: "-",
  });
}

const totals = results.reduce(
  (acc, result) => {
    acc.anchorFiles += 1;
    acc.anchors += result.anchors;
    acc.nonEmptyLines += result.nonEmptyLines;
    acc.uncoveredNonEmptyLines += result.uncoveredNonEmptyLines;
    acc.overlapLines += result.overlapLines;
    acc.badRanges += result.badRanges;
    if (result.status !== "passed") acc.failedFiles += 1;
    return acc;
  },
  {
    anchorFiles: 0,
    anchors: 0,
    nonEmptyLines: 0,
    uncoveredNonEmptyLines: 0,
    overlapLines: 0,
    badRanges: 0,
    failedFiles: 0,
  },
);

console.log(JSON.stringify({ totals, results }, null, 2));

process.exit(totals.failedFiles === 0 ? 0 : 1);
