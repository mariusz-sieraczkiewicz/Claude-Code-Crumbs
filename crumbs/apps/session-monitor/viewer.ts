import { existsSync, statSync, readFileSync, readdirSync, writeFileSync, mkdirSync, appendFileSync } from 'node:fs';
import { join, basename } from 'node:path';

const PROJECT_DIR = process.env.SESSION_MONITOR_PROJECT || process.cwd();
const ENCODED_PATH = '-' + PROJECT_DIR.replace(/\//g, '-').replace(/^-/, '');
const TRANSCRIPTS_DIR = join(process.env.HOME ?? '~', '.claude', 'projects', ENCODED_PATH);
const LOGS_DIR = join(import.meta.dir, 'logs');
const LOG_FILE = join(LOGS_DIR, '.viewer.log');
const SUMMARY_INTERVAL = 10_000;
const POLL_INTERVAL = 2_000;

if (!existsSync(LOGS_DIR)) mkdirSync(LOGS_DIR, { recursive: true });

function log(msg: string) {
  const ts = new Date().toISOString().slice(11, 19);
  const line = `[${ts}] ${msg}\n`;
  appendFileSync(LOG_FILE, line);
}

interface Entry {
  ts: string;
  type: 'progress' | 'turn' | 'summary';
  user?: string;
  agent?: string[];
  summary?: string;
}

interface ContentBlock {
  type: string;
  text?: string;
  name?: string;
  input?: Record<string, unknown>;
}

interface TranscriptLine {
  type: string;
  subtype?: string;
  promptId?: string;
  timestamp?: string;
  message?: { role?: string; content?: string | ContentBlock[] };
}

class TranscriptWatcher {
  sessionId: string;
  entries: Entry[] = [];
  private lastSize = 0;
  private buffer: Array<{text: string, ts: string}> = [];
  private lastSummary = '';
  private lastSummaryTime = 0;
  private pollTimer: ReturnType<typeof setInterval> | null = null;
  private summarizing = false;
  private userIntentEmitted = false;
  private turnSummaryPending = false;
  private pendingUserText: {text: string, ts: string} | null = null;
  private lastTranscriptTs: string = new Date().toISOString();

  constructor(sessionId: string) {
    this.sessionId = sessionId;
    this.loadState();
  }

  get transcriptPath() {
    return join(TRANSCRIPTS_DIR, `${this.sessionId}.jsonl`);
  }

  private get statePath() {
    return join(LOGS_DIR, `${this.sessionId}.state.json`);
  }

  private get entriesPath() {
    return join(LOGS_DIR, `${this.sessionId}.entries.jsonl`);
  }

  private loadState() {
    try {
      if (existsSync(this.statePath)) {
        const state = JSON.parse(readFileSync(this.statePath, 'utf-8'));
        this.lastSize = state.lastSize ?? 0;
        this.lastSummary = state.lastSummary ?? '';
      }
      if (existsSync(this.entriesPath)) {
        this.entries = readFileSync(this.entriesPath, 'utf-8')
          .split('\n').filter(Boolean)
          .map(l => JSON.parse(l));
      }
    } catch {}
  }

  private saveState() {
    writeFileSync(this.statePath, JSON.stringify({ lastSize: this.lastSize, lastSummary: this.lastSummary }));
  }

  private appendEntry(entry: Entry) {
    // Insert in chronological order (async SDK calls may return out of order)
    let insertIdx = this.entries.length;
    while (insertIdx > 0 && this.entries[insertIdx - 1]!.ts > entry.ts) {
      insertIdx--;
    }
    this.entries.splice(insertIdx, 0, entry);
    // Rewrite entries file to maintain order
    writeFileSync(this.entriesPath, this.entries.map(e => JSON.stringify(e)).join('\n') + '\n');
    this.saveState();
  }

  start() {
    this.lastSummaryTime = Date.now();
    if (this.lastSize === 0 && existsSync(this.transcriptPath)) {
      this.lastSize = statSync(this.transcriptPath).size;
      this.saveState();
    }
    log(`WATCH ${this.sessionId.slice(0,8)} from=${this.lastSize} entries=${this.entries.length}`);
    this.pollTimer = setInterval(() => this.poll(), POLL_INTERVAL);
  }

  stop() {
    if (this.pollTimer) { clearInterval(this.pollTimer); this.pollTimer = null; }
  }

  private poll() {
    if (!existsSync(this.transcriptPath)) return;
    const stat = statSync(this.transcriptPath);
    if (stat.size <= this.lastSize) {
      this.maybeFlushBuffer();
      return;
    }

    const diff = stat.size - this.lastSize;
    const buf = readFileSync(this.transcriptPath);
    const newPart = buf.slice(this.lastSize).toString('utf-8');
    this.lastSize = stat.size;
    const newLines = newPart.split('\n').filter(Boolean);
    log(`POLL +${diff}b ${newLines.length} lines buf=${this.buffer.length} pending=${!!this.pendingUserText} summarizing=${this.summarizing}`);

    for (const line of newLines) {
      try {
        this.processLine(JSON.parse(line));
      } catch {}
    }

    this.maybeFlushBuffer();
  }

  private processLine(entry: TranscriptLine) {
    if (entry.timestamp) this.lastTranscriptTs = entry.timestamp;
    const tType = entry.type + (entry.subtype ? ':' + entry.subtype : '');

    if (entry.type === 'user' && entry.message?.content) {
      const c = entry.message.content;
      let text = '';
      if (typeof c === 'string') text = c;
      else if (Array.isArray(c)) {
        const tb = c.find((b: ContentBlock) => b.type === 'text' && b.text);
        if (tb?.text) text = tb.text;
      }
      if (text && !text.startsWith('[') && text.length > 5 && !this.userIntentEmitted) {
        this.userIntentEmitted = true;
        this.pendingUserText = {text, ts: this.lastTranscriptTs};
        log(`USER_MSG queued: "${text.slice(0, 50)}"`);
      }
    }

    if (entry.type === 'assistant' && entry.message?.content && Array.isArray(entry.message.content)) {
      let textCount = 0, toolCount = 0;
      for (const block of entry.message.content) {
        if (block.type === 'text' && block.text) {
          this.buffer.push({text: block.text.slice(0, 500), ts: this.lastTranscriptTs});
          textCount++;
        }
        if (block.type === 'tool_use' && block.name) {
          const desc = this.describeToolUse(block.name, block.input ?? {});
          if (desc) { this.buffer.push({text: `[${desc}]`, ts: this.lastTranscriptTs}); toolCount++; }
        }
      }
      if (textCount || toolCount) log(`ASSISTANT text=${textCount} tools=${toolCount} buf=${this.buffer.length}`);
    }

    if (entry.type === 'system' && entry.subtype === 'turn_duration') {
      log(`TURN_END buf=${this.buffer.length} entries=${this.entries.length}`);
      this.userIntentEmitted = false;
      if (!this.turnSummaryPending) {
        this.turnSummaryPending = true;
        const frozenTs = this.lastTranscriptTs;
        this.flushTurnSummary(frozenTs).finally(() => { this.turnSummaryPending = false; });
      }
    }
  }

  private describeToolUse(name: string, input: Record<string, unknown>): string | null {
    const noisy = new Set(['Read', 'Glob', 'Grep', 'LSP', 'ListMcpResourcesTool', 'TaskList', 'TaskGet', 'CronList']);
    if (noisy.has(name)) return null;
    switch (name) {
      case 'Bash': return `Bash: ${String(input.description || input.command || '').slice(0, 60)}`;
      case 'Write': return `Write ${basename(String(input.file_path ?? ''))}`;
      case 'Edit': return `Edit ${basename(String(input.file_path ?? ''))}`;
      case 'Agent': return `Agent: ${String(input.description ?? '').slice(0, 50)}`;
      case 'Skill': return `Skill: ${String(input.skill ?? '')}`;
      default: return name.replace(/^mcp__\w+__/, '');
    }
  }

  private maybeFlushBuffer() {
    if (this.summarizing) { return; }
    if (this.pendingUserText) {
      log(`FLUSH_USER pending="${this.pendingUserText.text.slice(0, 30)}"`);
      this.flushAsProgress();
      return;
    }
    if (this.buffer.length === 0) return;
    const elapsed = Date.now() - this.lastSummaryTime;
    if (elapsed >= SUMMARY_INTERVAL) {
      log(`FLUSH_PROGRESS elapsed=${elapsed}ms buf=${this.buffer.length}`);
      this.flushAsProgress();
    }
  }

  private async flushAsProgress() {
    if (this.summarizing) return;
    // Emit user intent first (if pending)
    if (this.pendingUserText) {
      this.summarizing = true;
      const pending = this.pendingUserText;
      this.pendingUserText = null;
      try {
        log(`SDK_USER calling for "${pending.text.slice(0, 40)}"`);
        const intent = await this.summarizeUserIntent(pending.text);
        log(`SDK_USER result: "${intent?.slice(0, 60) ?? 'null'}"`);
        if (intent) {
          this.appendEntry({ ts: pending.ts, type: 'turn', user: intent });
        }
      } catch (e) { log(`SDK_USER error: ${e}`); }
      this.summarizing = false;
    }
    if (this.buffer.length === 0) return;
    this.summarizing = true;
    const bufferSnapshot = this.buffer.splice(0);
    const snapshotTs = bufferSnapshot[bufferSnapshot.length - 1]!.ts;
    this.lastSummaryTime = Date.now();

    try {
      const steps = await this.summarizeProgress(bufferSnapshot.map(b => b.text));
      if (steps && steps.length > 0) {
        this.appendEntry({ ts: snapshotTs, type: 'progress', agent: steps });
        this.lastSummary = steps.join(', ');
      }
    } catch {}
    this.summarizing = false;
  }

  private async summarizeUserIntent(text: string): Promise<string | null> {
    const prompt = `Jesteś obserwatorem sesji agenta. Skróć wiadomość użytkownika do esencji — max 10 słów. Zachowaj jego własne słowa i intencję. Opisz sytuację/prośbę, nie rozwiązanie.

Wiadomość użytkownika:
"${text.slice(0, 300).replace(/"/g, "'")}"

Odpowiedz samym skrótem, nic więcej. Przykłady:
"odpowiedziałem w czacie i czat zawisł, trzy kropki" → "Czat zawisł, trzy kropki"
"zmienianie portu jest irytujące, wybierz stały" → "Port ma być stały"
"nie widzę żadnych updateów" → "Brak updateów"
"zrób żeby markdown się renderował" → "Markdown ma się renderować"`;

    return this.callSDK(prompt);
  }

  private async flushTurnSummary(ts: string) {
    const remainingBuffer = this.buffer.splice(0);

    const turnSteps: string[] = [];
    for (let i = this.entries.length - 1; i >= 0; i--) {
      const e = this.entries[i]!;
      if (e.type === 'turn' && e.user) break;
      if (e.agent) turnSteps.unshift(...e.agent);
      if (e.summary) turnSteps.unshift(e.summary);
    }
    turnSteps.push(...remainingBuffer.map(b => b.text.slice(0, 100)));

    log(`TURN_SUMMARY steps=${turnSteps.length} remaining_buf=${remainingBuffer.length} summarizing=${this.summarizing}`);
    if (turnSteps.length === 0) { log(`TURN_SUMMARY skip: no steps`); return; }
    this.lastSummaryTime = Date.now();

    const prompt = `Jesteś obserwatorem sesji. Agent właśnie zakończył rundę pracy. Podsumuj ją zwięźle — krócej niż oryginalne kroki.

Kroki wykonane w tej rundzie:
${turnSteps.join('\n').slice(0, 2000)}

Odpowiedz jako JSON z max 2 krokami (czas przeszły) i jednozdaniowym statusem. Kroki grupuj — np. "edycja 3 plików" zamiast wymieniania każdego.

Przykład: {"steps":["Naprawiłem detekcję pytań w agent-runner","Przetestowałem na dev serverze"],"status":"Gotowe do review"}`;

    log(`SDK_SUMMARY calling with ${turnSteps.length} steps`);
    const raw = await this.callSDK(prompt);
    log(`SDK_SUMMARY result: "${raw?.slice(0, 80) ?? 'null'}"`);
    if (!raw) return;
    try {
      const match = raw.match(/\{[\s\S]*\}/);
      const parsed = JSON.parse(match ? match[0] : raw);
      if (parsed.steps || parsed.status) {
        this.appendEntry({
          ts,
          type: 'summary',
          agent: [...(parsed.steps || []), parsed.status ? `→ ${parsed.status}` : ''].filter(Boolean),
        });
        log(`SUMMARY_ENTRY created: ${JSON.stringify(parsed.steps?.slice(0,2))}`);
      }
    } catch (e) { log(`SDK_SUMMARY parse error: ${e}`); }
  }

  private async summarizeProgress(buffer: string[]): Promise<string[] | null> {
    log(`SDK_PROGRESS calling buf=${buffer.length}`);
    const prompt = `Jesteś obserwatorem sesji agenta. Na podstawie nowych kroków agenta napisz jedno zwięzłe hasło opisujące aktualną czynność.

Kontekst: monitorujesz live sesję agenta. Co ${SUMMARY_INTERVAL / 1000} sekund dostajesz nowe kroki i musisz napisać jedno hasło do dashboardu — ma oddawać CO agent faktycznie robi i DLACZEGO.

Poprzedni status: "${this.lastSummary || 'początek sesji'}"

Nowe kroki agenta:
${buffer.join('\n').slice(0, 2000)}

Odpowiedz jednym JSON array z dokładnie 1 elementem. Hasło w pierwszej osobie, max 6 słów. Opisz cel czynności, nie mechanikę.

Przykłady poprawnych odpowiedzi:
["Szukam przyczyny zawieszania czatu"]
["Analizuję wyniki wyszukiwania"]
["Porównuję opcje architektury"]
["Piszę podsumowanie raportu"]`;

    const raw = await this.callSDK(prompt);
    if (!raw) return null;
    try {
      const match = raw.match(/\[[\s\S]*\]/);
      return JSON.parse(match ? match[0] : raw);
    } catch {
      return [raw.slice(0, 80)];
    }
  }

  private async callSDK(prompt: string): Promise<string | null> {
    try {
      const sdk = await import('@anthropic-ai/claude-agent-sdk');
      const conversation = sdk.query({
        prompt,
        options: {
          permissionMode: 'bypassPermissions',
          allowDangerouslySkipPermissions: true,
          model: 'sonnet',
        },
      });

      let result = '';
      for await (const msg of conversation) {
        const m = msg as { type?: string; subtype?: string; result?: string; message?: { content?: ContentBlock[] } };
        if (m.type === 'assistant' && m.message?.content) {
          for (const block of m.message.content) {
            if (block.type === 'text' && block.text) result += block.text;
          }
        }
        if (m.type === 'result' && m.subtype === 'success' && m.result) {
          result = m.result;
        }
      }
      return result.trim() || null;
    } catch {
      return null;
    }
  }
}

// --- Server ---

const watchers = new Map<string, TranscriptWatcher>();
let activeSessionId: string | null = null;

function getSessionTitle(sessionId: string): string {
  const path = join(TRANSCRIPTS_DIR, `${sessionId}.jsonl`);
  try {
    const lines = readFileSync(path, 'utf-8').split('\n').slice(0, 30);
    for (const line of lines) {
      if (!line) continue;
      const entry = JSON.parse(line);
      if (entry.type === 'user' && entry.message?.content) {
        const c = entry.message.content;
        if (typeof c === 'string') return c.slice(0, 80);
        if (Array.isArray(c)) {
          const textBlock = c.find((b: ContentBlock) => b.type === 'text' && b.text);
          if (textBlock?.text) return textBlock.text.slice(0, 80);
        }
      }
    }
  } catch {}
  return '';
}

function isRealSession(sessionId: string): boolean {
  const path = join(TRANSCRIPTS_DIR, `${sessionId}.jsonl`);
  try {
    const stat = statSync(path);
    if (stat.size < 50_000) return false;
    const head = readFileSync(path, 'utf-8').slice(0, 2000);
    if (head.includes('Opisz tę turę sesji') || head.includes('Co nowego się dzieje')) return false;
    return true;
  } catch { return false; }
}

const server = Bun.serve({
  port: 7891,
  async fetch(req) {
    const url = new URL(req.url);

    if (url.pathname === '/') {
      return new Response(Bun.file(join(import.meta.dir, 'index.html')), {
        headers: { 'Content-Type': 'text/html; charset=utf-8' },
      });
    }

    if (url.pathname === '/api/sessions') {
      const limit = parseInt(url.searchParams.get('limit') ?? '10', 10);
      try {
        const files = readdirSync(TRANSCRIPTS_DIR)
          .filter(f => f.endsWith('.jsonl'))
          .filter(f => isRealSession(f.replace('.jsonl', '')))
          .map(f => {
            const fullPath = join(TRANSCRIPTS_DIR, f);
            const stat = statSync(fullPath);
            const id = f.replace('.jsonl', '');
            return { id, mtime: stat.mtimeMs, title: getSessionTitle(id) };
          })
          .sort((a, b) => b.mtime - a.mtime)
          .slice(0, limit);
        return Response.json(files);
      } catch {
        return Response.json([]);
      }
    }

    if (url.pathname === '/api/entries') {
      const sessionId = url.searchParams.get('session');
      const after = parseInt(url.searchParams.get('after') ?? '0', 10);
      if (!sessionId) return Response.json([]);
      const watcher = watchers.get(sessionId);
      if (!watcher) return Response.json([]);
      const entries = watcher.entries.slice(after).map((e, i) => ({ id: after + i + 1, ...e }));
      return Response.json(entries);
    }

    if (url.pathname === '/api/watch' && req.method === 'POST') {
      const body = await req.json() as { session?: string };
      const sessionId = body.session;
      if (!sessionId) return Response.json({ ok: false });

      activeSessionId = sessionId;
      if (!watchers.has(sessionId)) {
        const watcher = new TranscriptWatcher(sessionId);
        watchers.set(sessionId, watcher);
        watcher.start();
      }
      return Response.json({ ok: true, entries: watchers.get(sessionId)!.entries.length });
    }

    return new Response('Not found', { status: 404 });
  },
});

console.log(`Session Monitor: http://localhost:${server.port}`);
