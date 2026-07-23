"use client";

import { use, useEffect, useState } from "react";

import { BackLink, ErrorText, Loading } from "@/components/content";
import { getPublicProfile, type PublicUserProfile } from "@/lib/api";

export default function PublicProfilePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [profile, setProfile] = useState<PublicUserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPublicProfile(Number(id))
      .then(setProfile)
      .catch(() => setError("无法加载用户信息"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <Loading />;
  if (error || !profile) return <ErrorText message={error ?? "用户不存在"} />;

  const initial = profile.nickname?.[0] ?? "?";

  return (
    <div>
      <BackLink href="/interview" label="返回" />
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <div className="flex items-center gap-4">
          <span className="flex h-16 w-16 items-center justify-center overflow-hidden rounded-full bg-brand-100 text-2xl font-semibold text-brand-700">
            {profile.avatar_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={profile.avatar_url}
                alt={profile.nickname}
                className="h-full w-full object-cover"
              />
            ) : (
              initial
            )}
          </span>
          <div>
            <h1 className="text-xl font-bold text-slate-900">{profile.nickname}</h1>
            {profile.job_title && (
              <p className="text-sm text-slate-500">{profile.job_title}</p>
            )}
          </div>
        </div>

        {profile.bio && (
          <p className="mt-4 whitespace-pre-wrap text-sm text-slate-600">{profile.bio}</p>
        )}
      </div>
    </div>
  );
}
