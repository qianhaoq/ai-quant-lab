import fs from "node:fs/promises";
import path from "node:path";
import { runCommand, runShell, stripSensitiveEnv } from "./process.mjs";

export async function runCommandSequence(commands, cwd, title) {
  const results = [];

  for (const command of commands) {
    console.log(`\n[${title}] ${command}`);
    const result = await runShell(command, {
      cwd,
      env: stripSensitiveEnv(),
      stream: true,
    });
    results.push(result);
    if (result.code !== 0) {
      return {
        ok: false,
        failed: result,
        results,
      };
    }
  }

  return {
    ok: true,
    failed: null,
    results,
  };
}

export async function runCodex({ config, worktreePath, prompt, runDir }) {
  await fs.mkdir(runDir, { recursive: true });
  const logPath = path.join(runDir, "codex.jsonl");
  const env = stripSensitiveEnv(process.env, ["CODEX_API_KEY"]);

  console.log(`\n[Codex] ${config.codexCommand} ${config.codexArgs.join(" ")}`);
  const result = await runCommand(config.codexCommand, config.codexArgs, {
    cwd: worktreePath,
    env,
    input: prompt,
    stream: true,
  });

  await fs.writeFile(logPath, `${result.stdout}\n${result.stderr}`, "utf8");

  return {
    ...result,
    logPath,
  };
}
