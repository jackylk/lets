import { useMemo } from "react";
import { ContextBlock } from "../layout/ContextPane";
import type { MessageDTO } from "../api/types";
import { jumpToMessage } from "./jumpToMessage";

const HEALTH_KEYWORDS = [
  "肚子疼", "肚子痛", "腹痛", "胃痛", "胃疼", "腹泻", "拉肚子", "呕吐",
  "恶心", "发烧", "发热", "头疼", "头痛", "用药", "吃药", "布洛芬",
  "对乙酰氨基酚", "泰诺", "扑热息痛", "阿司匹林", "止痛药", "过敏",
  "ibuprofen", "acetaminophen", "aspirin",
];

interface HealthFact {
  label: string;
  value: string;
  sourceId?: number;
}

interface HealthFlag {
  label: string;
  matched: boolean;
  sourceId?: number;
}

interface HealthMedication {
  name: string;
  sourceId: number;
}

interface HealthContext {
  latestHumanMessage: MessageDTO | null;
  facts: HealthFact[];
  redFlags: HealthFlag[];
  missingQuestions: string[];
  medications: HealthMedication[];
}

export function isHealthTopic(messages: MessageDTO[], title = ""): boolean {
  const text = `${title}\n${messages.map((m) => m.body).join("\n")}`.toLowerCase();
  return HEALTH_KEYWORDS.some((kw) => text.includes(kw.toLowerCase()));
}

export function buildHealthContext(messages: MessageDTO[]): HealthContext {
  const humanChats = messages.filter((m) => m.actor_type === "human" && m.type === "chat");
  const latestHumanMessage = humanChats[humanChats.length - 1] ?? null;
  const text = humanChats.map((m) => m.body).join("\n");

  const facts: HealthFact[] = [];
  if (latestHumanMessage) {
    facts.push({
      label: "当前描述",
      value: latestHumanMessage.body,
      sourceId: latestHumanMessage.id,
    });
  }
  addFirstMatch(facts, humanChats, "开始时间", /(刚刚|今天|昨晚|昨天|前天|[0-9一二三四五六七八九十]+[个]?(小时|天|分钟)前?|持续[^\s，。；]*)/);
  addFirstMatch(facts, humanChats, "疼痛位置", /(右下腹|左下腹|上腹|下腹|肚脐周围|胃部|腹部|肚子|小腹)/);
  addFirstMatch(facts, humanChats, "伴随症状", /(发烧|发热|呕吐|恶心|腹泻|拉肚子|便血|黑便|头晕|出冷汗)/);

  const redFlags = [
    flag(humanChats, "剧烈或持续加重的腹痛", /(剧烈|严重|痛到|受不了|加重|越来越痛)/),
    flag(humanChats, "发热或明显全身不适", /(发烧|发热|寒战|全身无力)/),
    flag(humanChats, "呕血、便血或黑便", /(呕血|吐血|便血|血便|黑便|柏油样)/),
    flag(humanChats, "持续呕吐或明显脱水", /(一直吐|持续呕吐|喝不下|尿很少|脱水)/),
    flag(humanChats, "怀孕、近期手术或腹部外伤", /(怀孕|孕|手术|外伤|撞到|摔到)/),
    flag(humanChats, "胸痛、晕厥或呼吸困难", /(胸痛|胸闷|晕倒|昏厥|呼吸困难|喘不上气)/),
  ];

  const medications = collectMedications(humanChats);
  const missingQuestions = [
    hasAny(text, /(右下腹|左下腹|上腹|下腹|肚脐周围|胃部|腹部|肚子|小腹)/) ? null : "疼痛具体位置在哪里？",
    hasAny(text, /(刚刚|今天|昨晚|昨天|前天|小时|分钟|天|持续)/) ? null : "从什么时候开始，持续多久了？",
    hasAny(text, /(1|2|3|4|5|6|7|8|9|10|轻微|中等|剧烈|严重)/) ? null : "疼痛强度 0-10 分大概几分？",
    hasAny(text, /(发烧|发热|体温|呕吐|恶心|腹泻|拉肚子|便血|黑便)/) ? null : "有没有发热、呕吐、腹泻、便血或黑便？",
    medications.length > 0 ? null : "已经吃过什么药？剂量和时间是什么？",
    hasAny(text, /(过敏|孕|怀孕|胃溃疡|肝|肾|高血压|抗凝|儿童|老人)/) ? null : "有没有药物过敏、怀孕、胃溃疡、肝肾问题或正在吃的药？",
  ].filter(Boolean) as string[];

  return { latestHumanMessage, facts, redFlags, missingQuestions, medications };
}

export function HealthContextPane({ messages }: { messages: MessageDTO[] }) {
  const ctx = useMemo(() => buildHealthContext(messages), [messages]);
  const matchedRedFlags = ctx.redFlags.filter((f) => f.matched);

  return (
    <>
      <div className="px-1 text-[11px] leading-relaxed text-text-dim">
        健康求助模式：agent 帮你和家人整理症状、用药记录和危险信号；不替代医生诊断。
      </div>

      <ContextBlock label="当前情况" hint="从聊天里自动整理出的症状和时间线">
        <div className="flex flex-col gap-2">
          {ctx.facts.length > 0 ? (
            ctx.facts.map((f) => <FactCard key={f.label} fact={f} />)
          ) : (
            <EmptyHealth>先描述哪里不舒服、什么时候开始、现在有多严重。</EmptyHealth>
          )}
        </div>
      </ContextBlock>

      <ContextBlock
        label="危险信号"
        right={matchedRedFlags.length > 0 ? `${matchedRedFlags.length}` : undefined}
        hint="出现这些情况时，应优先考虑及时就医"
      >
        <div className="flex flex-col gap-1.5">
          {ctx.redFlags.map((f) => (
            <button
              key={f.label}
              type="button"
              onClick={() => f.sourceId && jumpToMessage(f.sourceId)}
              className={
                "w-full rounded border px-2.5 py-1.5 text-left text-[12.5px] " +
                (f.matched
                  ? "border-accent-border bg-accent-soft text-accent-text"
                  : "border-border-soft bg-surface-elev text-text-dim")
              }
            >
              <span className="font-mono text-[10px] uppercase mr-1.5">
                {f.matched ? "提到" : "未确认"}
              </span>
              {f.label}
            </button>
          ))}
        </div>
      </ContextBlock>

      <ContextBlock
        label="待确认"
        right={ctx.missingQuestions.length > 0 ? `${ctx.missingQuestions.length}` : undefined}
        hint="家人或 agent 下一步应该先问清楚的信息"
      >
        {ctx.missingQuestions.length > 0 ? (
          <div className="flex flex-col gap-1.5">
            {ctx.missingQuestions.map((q) => (
              <div key={q} className="rounded border border-dashed border-border bg-surface-elev px-2.5 py-1.5 text-[12.5px] text-text-muted">
                {q}
              </div>
            ))}
          </div>
        ) : (
          <EmptyHealth>关键信息基本齐了，继续记录变化和已采取措施。</EmptyHealth>
        )}
      </ContextBlock>

      <ContextBlock
        label="用药记录"
        right={ctx.medications.length > 0 ? `${ctx.medications.length}` : undefined}
        hint="只记录和提醒风险，不替代医生或药师建议"
      >
        <div className="flex flex-col gap-2">
          {ctx.medications.length > 0 ? (
            ctx.medications.map((m) => (
              <button
                key={`${m.name}-${m.sourceId}`}
                type="button"
                onClick={() => jumpToMessage(m.sourceId)}
                className="rounded border border-border-soft bg-surface-elev px-2.5 py-1.5 text-left text-[12.5px] text-text hover:border-accent-border"
              >
                {m.name}
                <div className="mt-1 text-[10.5px] text-text-dim">点击看提到这次用药的消息</div>
              </button>
            ))
          ) : (
            <EmptyHealth>还没有记录药名、剂量和服用时间。</EmptyHealth>
          )}
          <div className="rounded border border-border-soft bg-surface-elev p-2.5 text-[11.5px] leading-relaxed text-text-dim">
            用药前先核对说明书、年龄/孕期/过敏/基础病；不要重复服用含同一成分的药。腹痛时尤其要谨慎使用 NSAIDs 类止痛药，拿不准时先问医生或药师。
          </div>
        </div>
      </ContextBlock>

      <ContextBlock label="下一步" hint="按风险分流，而不是直接给诊断">
        <div className="rounded border border-border-soft bg-surface-elev p-2.5 text-[12.5px] leading-relaxed text-text">
          {matchedRedFlags.length > 0 ? (
            <span>已提到危险信号。建议尽快联系医生、急诊或当地急救服务，不要只在家里自行用药观察。</span>
          ) : (
            <span>先补齐待确认信息，记录症状变化和已用药。如果疼痛加重、持续不缓解，或出现危险信号，应及时就医。</span>
          )}
        </div>
      </ContextBlock>
    </>
  );
}

function EmptyHealth({ children }: { children: string }) {
  return (
    <div className="rounded border border-dashed border-border p-3 text-center text-[12px] italic text-text-dim">
      {children}
    </div>
  );
}

function FactCard({ fact }: { fact: HealthFact }) {
  return (
    <button
      type="button"
      onClick={() => fact.sourceId && jumpToMessage(fact.sourceId)}
      className="rounded border border-border-soft bg-surface-elev p-2.5 text-left hover:border-accent-border"
    >
      <div className="text-[10.5px] font-semibold uppercase tracking-wider text-text-dim">{fact.label}</div>
      <div className="mt-1 text-[13px] leading-relaxed text-text">{fact.value}</div>
    </button>
  );
}

function addFirstMatch(
  facts: HealthFact[],
  messages: MessageDTO[],
  label: string,
  pattern: RegExp,
) {
  for (const m of messages) {
    const match = m.body.match(pattern);
    if (!match) continue;
    facts.push({ label, value: match[0], sourceId: m.id });
    return;
  }
}

function flag(messages: MessageDTO[], label: string, pattern: RegExp): HealthFlag {
  for (const m of messages) {
    if (pattern.test(m.body)) return { label, matched: true, sourceId: m.id };
  }
  return { label, matched: false };
}

function hasAny(text: string, pattern: RegExp): boolean {
  return pattern.test(text);
}

function collectMedications(messages: MessageDTO[]): HealthMedication[] {
  const meds = [
    "布洛芬", "对乙酰氨基酚", "泰诺", "扑热息痛", "阿司匹林", "萘普生",
    "蒙脱石散", "奥美拉唑", "铝碳酸镁", "藿香正气", "ibuprofen",
    "acetaminophen", "aspirin", "naproxen",
  ];
  const out: HealthMedication[] = [];
  const seen = new Set<string>();
  for (const m of messages) {
    const lower = m.body.toLowerCase();
    for (const med of meds) {
      if (!lower.includes(med.toLowerCase())) continue;
      const key = med.toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      out.push({ name: med, sourceId: m.id });
    }
  }
  return out;
}
