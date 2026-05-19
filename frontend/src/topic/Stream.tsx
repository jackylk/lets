import type { MessageDTO } from "../api/types";
import { Message } from "../messages/Message";
import { makeActorResolver, type Directory } from "../messages/actorResolver";
import { DaySeparator } from "./DaySeparator";

interface Props {
  messages: MessageDTO[];
  directory: Directory;
}

function dayLabel(iso: string): string {
  return new Date(iso).toLocaleDateString("zh-CN");
}

export function Stream({ messages, directory }: Props) {
  const resolve = makeActorResolver(directory);
  let lastDay: string | null = null;

  return (
    <div className="flex flex-col">
      {messages.map((m) => {
        const day = dayLabel(m.created_at);
        const showDay = day !== lastDay;
        lastDay = day;
        return (
          <div key={m.id}>
            {showDay && <DaySeparator label={day} />}
            <Message message={m} resolveActor={resolve} />
          </div>
        );
      })}
    </div>
  );
}
