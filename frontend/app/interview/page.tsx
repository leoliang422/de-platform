"use client";

import { useEffect, useState } from "react";

import { Empty, ErrorText, ListCard, Loading, PageHeader } from "@/components/content";
import { getCompanies, type Company } from "@/lib/api";

export default function InterviewPage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCompanies()
      .then(setCompanies)
      .catch(() => setError("无法加载企业列表，请确认后端已启动"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <PageHeader title="面经" desc="按企业组织的真实面试经验" />
      {loading ? (
        <Loading />
      ) : error ? (
        <ErrorText message={error} />
      ) : companies.length === 0 ? (
        <Empty message="暂无企业" />
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {companies.map((c) => (
            <ListCard key={c.id} href={`/interview/${c.id}`}>
              <span className="font-medium text-slate-900">{c.name}</span>
            </ListCard>
          ))}
        </div>
      )}
    </div>
  );
}
