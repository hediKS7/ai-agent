import ChatShell from "@/components/layout/ChatShell";

const DEFAULT_USER_ID = "988367fd-3496-401a-8c7c-3336a3523079";

export default function Home() {
  return <ChatShell userId={DEFAULT_USER_ID} username="vistasyintern" />;
}
