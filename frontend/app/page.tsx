import { ChatWorkspace } from "@/components/chat/workspace";

const DEFAULT_USER_ID = process.env.NEXT_PUBLIC_DEMO_USER_ID ?? "988367fd-3496-401a-8c7c-3336a3523079";

export default function Home() {
  return <ChatWorkspace userId={DEFAULT_USER_ID} username="vistasyintern" />;
}
