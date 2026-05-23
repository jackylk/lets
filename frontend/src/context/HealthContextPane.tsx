import { useMemo, useState } from "react";
import { ContextBlock } from "../layout/ContextPane";
import type { MessageDTO } from "../api/types";
import { jumpToMessage } from "./jumpToMessage";
import { useIdentityMe, usePostMessage } from "../api/queries";

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

interface HealthSuggestion {
  title: string;
  body: string;
  tone: "urgent" | "caution" | "plain";
}

interface HealthQuestion {
  id: string;
  prompt: string;
  quickAnswers: string[];
  placeholder: string;
}

interface HealthContext {
  latestHumanMessage: MessageDTO | null;
  facts: HealthFact[];
  redFlags: HealthFlag[];
  missingQuestions: HealthQuestion[];
  medications: HealthMedication[];
  suggestions: HealthSuggestion[];
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
  const matchedRedFlags = redFlags.filter((f) => f.matched);
  const missingQuestions = [
    hasAny(text, /(右下腹|左下腹|上腹|下腹|肚脐周围|胃部|腹部|肚子|小腹)/)
      ? null
      : question("location", "疼痛具体位置在哪里？", ["上腹", "下腹", "肚脐周围", "说不清"], "比如：右下腹、胃部、肚脐周围；按压会不会更痛"),
    hasAny(text, /(刚刚|今天|昨晚|昨天|前天|小时|分钟|天|持续)/)
      ? null
      : question("started", "从什么时候开始，持续多久了？", ["刚刚", "今天", "昨晚", "不确定"], "比如：今天中午开始，阵痛/一直痛，持续约 2 小时"),
    hasAny(text, /(1|2|3|4|5|6|7|8|9|10|轻微|中等|剧烈|严重)/)
      ? null
      : question("severity", "疼痛强度 0-10 分大概几分？", ["1-3 轻微", "4-6 中等", "7-10 很痛", "说不清"], "也可以写：能不能正常走路、睡觉、说话"),
    hasAny(text, /(发烧|发热|体温|呕吐|恶心|腹泻|拉肚子|便血|黑便)/)
      ? null
      : question("symptoms", "有没有发热、呕吐、腹泻、便血或黑便？", ["没有", "有", "不确定"], "如果有，写体温、吐了几次、腹泻几次、便血/黑便情况"),
    medications.length > 0
      ? null
      : question("medication", "已经吃过什么药？剂量和时间是什么？", ["还没吃药", "吃过", "不确定"], "比如：布洛芬 1 片，13:00 吃；或写还吃了哪些药"),
    hasAny(text, /(过敏|孕|怀孕|胃溃疡|肝|肾|高血压|抗凝|儿童|老人)/)
      ? null
      : question("risk", "有没有药物过敏、怀孕、胃溃疡、肝肾问题或正在吃的药？", ["没有", "有", "不确定"], "如果有，写具体情况；如果拿不准就写不确定"),
  ].filter(Boolean) as HealthQuestion[];

  const suggestions = buildSuggestions({
    text,
    medications,
    hasRedFlags: matchedRedFlags.length > 0,
    missingQuestions,
  });

  return { latestHumanMessage, facts, redFlags, missingQuestions, medications, suggestions };
}

export function HealthContextPane({ messages, topicId }: { messages: MessageDTO[]; topicId?: number }) {
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
              <MissingQuestionCard key={q.id} question={q} topicId={topicId} />
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
            用药前先核对说明书、年龄/孕期/过敏/基础病；不要重复服用含同一成分的药。腹痛时尤其要谨慎使用布洛芬、萘普生等非甾体抗炎止痛药，拿不准时先问医生或药师。
          </div>
        </div>
      </ContextBlock>

      <ContextBlock
        label="建议"
        right={ctx.suggestions.length > 0 ? `${ctx.suggestions.length}` : undefined}
        hint="包含观察、用药方向、联系医生或去医院的建议"
      >
        <div className="flex flex-col gap-2">
          {ctx.suggestions.map((s) => (
            <SuggestionCard key={s.title} suggestion={s} />
          ))}
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

function MissingQuestionCard({
  question,
  topicId,
}: {
  question: HealthQuestion;
  topicId?: number;
}) {
  if (topicId == null) {
    return (
      <div className="rounded border border-dashed border-border bg-surface-elev px-2.5 py-1.5 text-[12.5px] text-text-muted">
        {question.prompt}
      </div>
    );
  }
  return <AnswerableMissingQuestionCard question={question} topicId={topicId} />;
}

function AnswerableMissingQuestionCard({
  question,
  topicId,
}: {
  question: HealthQuestion;
  topicId: number;
}) {
  const [open, setOpen] = useState(false);
  const [answer, setAnswer] = useState("");
  const [detail, setDetail] = useState("");
  const [sent, setSent] = useState(false);
  const me = useIdentityMe();
  const post = usePostMessage(topicId);
  const canPost = me.data?.human.id != null;
  const trimmedAnswer = answer.trim();
  const trimmedDetail = detail.trim();

  function submit() {
    if (!canPost || !trimmedAnswer || post.isPending) return;
    const body = [
      "补充健康信息：",
      `- ${question.prompt} ${trimmedAnswer}`,
      trimmedDetail ? `- 补充：${trimmedDetail}` : null,
    ].filter(Boolean).join("\n");
    post.mutate({
      topic_id: topicId,
      type: "chat",
      actor_type: "human",
      actor_id: me.data!.human.id,
      body,
      metadata: { source: "health_context_question", question_id: question.id },
    }, {
      onSuccess: () => {
        setSent(true);
        setOpen(false);
        setAnswer("");
        setDetail("");
      },
    });
  }

  return (
    <div className="rounded border border-dashed border-border bg-surface-elev px-2.5 py-2 text-[12.5px] text-text-muted">
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1 leading-relaxed">{question.prompt}</div>
        {canPost && (
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="shrink-0 rounded-[3px] border border-border-soft px-2 py-0.5 text-[11px] text-text-dim hover:border-accent-border hover:text-accent-text"
          >
            {open ? "收起" : sent ? "再补充" : "回答"}
          </button>
        )}
      </div>

      {sent && !open && (
        <div className="mt-1.5 text-[11px] text-text-dim">已发到聊天里，agent 会看到这条补充。</div>
      )}

      {open && (
        <div className="mt-2 flex flex-col gap-2">
          <div className="flex flex-wrap gap-1.5">
            {question.quickAnswers.map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => setAnswer(option)}
                className={
                  "rounded-[3px] border px-2 py-1 text-[11.5px] " +
                  (answer === option
                    ? "border-accent-border bg-accent-soft text-accent-text"
                    : "border-border-soft bg-bg text-text-dim hover:border-border hover:text-text")
                }
              >
                {option}
              </button>
            ))}
          </div>
          <textarea
            rows={2}
            value={detail}
            onChange={(e) => setDetail(e.target.value)}
            placeholder={question.placeholder}
            className="min-h-[58px] w-full resize-none rounded border border-border-soft bg-bg px-2 py-1.5 text-[12px] leading-relaxed text-text outline-none placeholder:text-text-dim focus:border-accent-border"
          />
          <div className="flex items-center justify-between gap-2">
            <input
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="也可以直接输入答案"
              className="min-w-0 flex-1 rounded border border-border-soft bg-bg px-2 py-1.5 text-[12px] text-text outline-none placeholder:text-text-dim focus:border-accent-border"
            />
            <button
              type="button"
              disabled={!trimmedAnswer || post.isPending}
              onClick={submit}
              className="shrink-0 rounded-[3px] bg-text px-3 py-1.5 text-[12px] text-bg disabled:cursor-not-allowed disabled:opacity-40"
            >
              {post.isPending ? "发送中" : "发送"}
            </button>
          </div>
        </div>
      )}
    </div>
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

function SuggestionCard({ suggestion }: { suggestion: HealthSuggestion }) {
  const tone =
    suggestion.tone === "urgent"
      ? "border-accent-border bg-accent-soft text-accent-text"
      : suggestion.tone === "caution"
        ? "border-border bg-surface-elev text-text"
        : "border-border-soft bg-surface-elev text-text";
  return (
    <div className={`rounded border p-2.5 ${tone}`}>
      <div className="text-[12.5px] font-semibold">{suggestion.title}</div>
      <div className="mt-1 text-[11.5px] leading-relaxed">{suggestion.body}</div>
    </div>
  );
}

function buildSuggestions({
  text,
  medications,
  hasRedFlags,
  missingQuestions,
}: {
  text: string;
  medications: HealthMedication[];
  hasRedFlags: boolean;
  missingQuestions: HealthQuestion[];
}): HealthSuggestion[] {
  if (hasRedFlags) {
    return [
      {
        title: "优先去医院 / 急诊",
        body: "已经提到危险信号。不要只靠自行用药观察，建议尽快联系医生、急诊或当地急救服务。",
        tone: "urgent",
      },
      {
        title: "带上用药和症状记录",
        body: "就医时带上疼痛开始时间、位置、强度、伴随症状，以及已经吃过的药名、剂量和时间。",
        tone: "plain",
      },
    ];
  }

  const suggestions: HealthSuggestion[] = [
    {
      title: "先补齐关键信息",
      body: missingQuestions.length > 0
        ? "现在还缺少一些用药前关键信息。先确认疼痛位置、持续时间、严重程度、伴随症状和过敏/基础病。"
        : "关键信息基本齐了。继续记录症状变化、体温和已采取措施。",
      tone: "plain",
    },
    {
      title: "可先做低风险护理",
      body: "在没有危险信号时，可以先休息、少量多次补水、清淡饮食，避免酒精和刺激性食物，并观察是否加重。",
      tone: "plain",
    },
  ];

  if (hasAny(text, /(腹泻|拉肚子|呕吐)/)) {
    suggestions.push({
      title: "腹泻/呕吐时优先防脱水",
      body: "重点是补液和观察尿量、精神状态。若持续呕吐、喝不下水、明显脱水或便血，应及时就医。",
      tone: "caution",
    });
  }

  if (hasAny(text, /(胃痛|胃疼|上腹|烧心|反酸)/)) {
    suggestions.push({
      title: "像胃部不适时可问药师",
      body: "如果更像烧心、反酸或胃部不适，可以咨询药师是否适合抗酸/胃部不适类非处方药；有黑便、呕血或剧烈疼痛则不要自行处理。",
      tone: "caution",
    });
  }

  suggestions.push({
    title: "止痛/退热药要谨慎",
    body: "如果考虑非处方止痛或退热药，先核对说明书和禁忌。腹痛时不要盲目用布洛芬、萘普生等非甾体抗炎止痛药；有胃溃疡、肾病、抗凝药、孕期等情况尤其要先问医生/药师。",
    tone: "caution",
  });

  if (medications.some((m) => /对乙酰氨基酚|泰诺|扑热息痛|acetaminophen/i.test(m.name))) {
    suggestions.push({
      title: "注意对乙酰氨基酚重复成分",
      body: "很多感冒药/止痛药都可能含对乙酰氨基酚。不要和其他同成分药重复服用，避免超量；肝病或饮酒情况更要谨慎。",
      tone: "caution",
    });
  }

  if (medications.length > 0) {
    suggestions.push({
      title: "补充剂量和时间",
      body: "已提到药名，但还需要记录剂量、服用时间、是否还吃了其他药，方便判断是否重复或超量。",
      tone: "plain",
    });
  } else {
    suggestions.push({
      title: "用药前先问清禁忌",
      body: "还没有用药记录。吃药前先确认年龄、是否怀孕、过敏史、胃溃疡、肝肾问题、正在服用的药；拿不准时问医生或药师。",
      tone: "plain",
    });
  }

  return suggestions;
}

function question(
  id: string,
  prompt: string,
  quickAnswers: string[],
  placeholder: string,
): HealthQuestion {
  return { id, prompt, quickAnswers, placeholder };
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
