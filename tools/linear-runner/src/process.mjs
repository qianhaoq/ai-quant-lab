import { spawn } from "node:child_process";

const SENSITIVE_ENV_PATTERNS = [
  /API[_-]?KEY/i,
  /SECRET/i,
  /TOKEN/i,
  /PASSWORD/i,
  /PRIVATE/i,
  /CREDENTIAL/i,
];

export function stripSensitiveEnv(env = process.env, allowList = []) {
  const allowed = new Set(allowList);
  const next = { ...env };

  for (const key of Object.keys(next)) {
    if (allowed.has(key)) {
      continue;
    }
    if (SENSITIVE_ENV_PATTERNS.some((pattern) => pattern.test(key))) {
      delete next[key];
    }
  }

  return next;
}

export function shellSplit(value) {
  if (!value || !value.trim()) {
    return [];
  }

  const result = [];
  let current = "";
  let quote = null;
  let escaped = false;

  for (const char of value) {
    if (escaped) {
      current += char;
      escaped = false;
      continue;
    }

    if (char === "\\") {
      escaped = true;
      continue;
    }

    if (quote) {
      if (char === quote) {
        quote = null;
      } else {
        current += char;
      }
      continue;
    }

    if (char === "'" || char === "\"") {
      quote = char;
      continue;
    }

    if (/\s/.test(char)) {
      if (current) {
        result.push(current);
        current = "";
      }
      continue;
    }

    current += char;
  }

  if (escaped) {
    current += "\\";
  }
  if (quote) {
    throw new Error(`命令参数包含未闭合引号：${value}`);
  }
  if (current) {
    result.push(current);
  }

  return result;
}

export function splitCommandList(value, fallback) {
  const source = value?.trim() ? value : fallback;
  return source
    .split(/\r?\n|\|/g)
    .map((item) => item.trim())
    .filter(Boolean);
}

export async function runCommand(command, args = [], options = {}) {
  const {
    cwd,
    env = process.env,
    input,
    stream = false,
    timeoutMs,
    title = `${command} ${args.join(" ")}`.trim(),
  } = options;

  return new Promise((resolve) => {
    const child = spawn(command, args, {
      cwd,
      env,
      stdio: ["pipe", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";
    let timedOut = false;
    let timer = null;

    if (timeoutMs) {
      timer = setTimeout(() => {
        timedOut = true;
        child.kill("SIGTERM");
      }, timeoutMs);
    }

    child.stdout.on("data", (chunk) => {
      const text = chunk.toString();
      stdout += text;
      if (stream) {
        process.stdout.write(text);
      }
    });

    child.stderr.on("data", (chunk) => {
      const text = chunk.toString();
      stderr += text;
      if (stream) {
        process.stderr.write(text);
      }
    });

    child.on("error", (error) => {
      if (timer) {
        clearTimeout(timer);
      }
      resolve({
        code: 127,
        stdout,
        stderr: `${stderr}${error.message}`,
        timedOut,
        title,
      });
    });

    child.on("close", (code) => {
      if (timer) {
        clearTimeout(timer);
      }
      resolve({
        code: timedOut ? 124 : code ?? 0,
        stdout,
        stderr,
        timedOut,
        title,
      });
    });

    if (input) {
      child.stdin.write(input);
    }
    child.stdin.end();
  });
}

export async function runShell(command, options = {}) {
  const shell = process.platform === "win32" ? "cmd.exe" : "bash";
  const args = process.platform === "win32" ? ["/d", "/s", "/c", command] : ["-lc", command];
  return runCommand(shell, args, {
    ...options,
    title: command,
  });
}

export async function assertCommandExists(command) {
  const result = await runCommand(command, ["--version"], {
    env: stripSensitiveEnv(),
  });
  if (result.code !== 0) {
    throw new Error(`缺少命令：${command}。请先安装并完成登录/配置。`);
  }
}

export function requireSuccess(result) {
  if (result.code !== 0) {
    const tail = `${result.stdout}\n${result.stderr}`.trim().slice(-4000);
    throw new Error(`命令失败：${result.title}\n${tail}`);
  }
  return result;
}
