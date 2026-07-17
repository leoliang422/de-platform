"use client";

import { useEffect, useState, type FormEvent } from "react";

import { PageHeader } from "@/components/content";
import { RequireAuth } from "@/components/guard";
import { useAuth } from "@/lib/auth";
import {
  ApiError,
  changeMyPassword,
  getAccessToken,
  updateMyProfile,
  uploadImage,
} from "@/lib/api";

export default function SettingsPage() {
  return (
    <RequireAuth>
      <SettingsInner />
    </RequireAuth>
  );
}

const inputCls =
  "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none";

function SettingsInner() {
  const { user, refreshUser } = useAuth();

  const [nickname, setNickname] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [bio, setBio] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileMsg, setProfileMsg] = useState<string | null>(null);
  const [profileErr, setProfileErr] = useState<string | null>(null);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);

  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [savingPw, setSavingPw] = useState(false);
  const [pwMsg, setPwMsg] = useState<string | null>(null);
  const [pwErr, setPwErr] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    setNickname(user.nickname ?? "");
    setJobTitle(user.job_title ?? "");
    setBio(user.bio ?? "");
    setAvatarUrl(user.avatar_url ?? "");
  }, [user]);

  async function handleAvatarFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const token = getAccessToken();
    if (!token) return;
    setUploadingAvatar(true);
    setProfileErr(null);
    try {
      const { url } = await uploadImage(token, file);
      setAvatarUrl(url);
      setProfileMsg("头像已上传，记得点「保存资料」生效。");
    } catch (err) {
      setProfileErr(err instanceof ApiError ? err.message : "上传失败");
    } finally {
      setUploadingAvatar(false);
      e.target.value = "";
    }
  }

  async function handleProfile(e: FormEvent) {
    e.preventDefault();
    const token = getAccessToken();
    if (!token) return;
    setSavingProfile(true);
    setProfileMsg(null);
    setProfileErr(null);
    try {
      await updateMyProfile(token, {
        nickname,
        job_title: jobTitle || null,
        bio: bio || null,
        avatar_url: avatarUrl || null,
      });
      await refreshUser();
      setProfileMsg("资料已更新。");
    } catch (err) {
      setProfileErr(err instanceof ApiError ? err.message : "保存失败");
    } finally {
      setSavingProfile(false);
    }
  }

  async function handlePassword(e: FormEvent) {
    e.preventDefault();
    const token = getAccessToken();
    if (!token) return;
    setPwMsg(null);
    setPwErr(null);
    if (newPassword !== confirmPassword) {
      setPwErr("两次输入的新密码不一致。");
      return;
    }
    setSavingPw(true);
    try {
      await changeMyPassword(token, {
        old_password: oldPassword,
        new_password: newPassword,
      });
      setPwMsg("密码已修改，请牢记新密码。");
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setPwErr(err instanceof ApiError ? err.message : "修改失败");
    } finally {
      setSavingPw(false);
    }
  }

  return (
    <div>
      <PageHeader title="账号设置" desc="编辑个人资料与修改密码" />

      <form
        onSubmit={handleProfile}
        className="mb-8 space-y-4 rounded-xl border border-slate-200 bg-white p-5"
      >
        <h2 className="text-base font-semibold text-slate-900">个人资料</h2>

        <div className="flex items-center gap-4">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={avatarUrl || "https://api.dicebear.com/7.x/initials/svg?seed=" + (nickname || "U")}
            alt="头像预览"
            className="h-16 w-16 rounded-full border border-slate-200 object-cover"
          />
          <div className="flex-1">
            <label className="mb-1 block text-sm font-medium text-slate-700">头像</label>
            <div className="flex items-center gap-3">
              <label className="cursor-pointer rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50">
                {uploadingAvatar ? "上传中…" : "上传图片"}
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/gif,image/webp"
                  onChange={handleAvatarFile}
                  disabled={uploadingAvatar}
                  className="hidden"
                />
              </label>
              <span className="text-xs text-slate-400">或直接填链接（≤5MB，PNG/JPG/GIF/WEBP）</span>
            </div>
            <input
              value={avatarUrl}
              onChange={(e) => setAvatarUrl(e.target.value)}
              placeholder="https://…"
              className={`${inputCls} mt-2`}
            />
          </div>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">昵称</label>
          <input
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            required
            maxLength={50}
            className={inputCls}
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">职业标签</label>
          <input
            value={jobTitle}
            onChange={(e) => setJobTitle(e.target.value)}
            placeholder="如：数据工程师 / 数据分析师"
            maxLength={100}
            className={inputCls}
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">简介</label>
          <textarea
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            rows={3}
            maxLength={500}
            className={inputCls}
          />
        </div>

        {profileErr && <p className="text-sm text-red-600">{profileErr}</p>}
        {profileMsg && <p className="text-sm text-green-600">{profileMsg}</p>}

        <button
          type="submit"
          disabled={savingProfile}
          className="rounded-lg bg-brand-600 px-5 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {savingProfile ? "保存中…" : "保存资料"}
        </button>
      </form>

      <form
        onSubmit={handlePassword}
        className="space-y-4 rounded-xl border border-slate-200 bg-white p-5"
      >
        <h2 className="text-base font-semibold text-slate-900">修改密码</h2>

        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">当前密码</label>
          <input
            type="password"
            value={oldPassword}
            onChange={(e) => setOldPassword(e.target.value)}
            required
            className={inputCls}
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">新密码（至少 6 位）</label>
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            minLength={6}
            className={inputCls}
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">确认新密码</label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            minLength={6}
            className={inputCls}
          />
        </div>

        {pwErr && <p className="text-sm text-red-600">{pwErr}</p>}
        {pwMsg && <p className="text-sm text-green-600">{pwMsg}</p>}

        <button
          type="submit"
          disabled={savingPw}
          className="rounded-lg bg-brand-600 px-5 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {savingPw ? "提交中…" : "修改密码"}
        </button>
      </form>
    </div>
  );
}
