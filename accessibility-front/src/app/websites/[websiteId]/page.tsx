import Website from "@/components/Website";
import { User } from "@/lib/types/user";
import { getCurrentUser } from "next-cas-client/app";


async function page({ params }: { params: Promise<{ websiteId: string }> }) {
  const { websiteId } = await params;
  const user = await getCurrentUser<User>();
  return (
    <Website user={user} websiteId={Number(websiteId)} />
  )
}

export default page