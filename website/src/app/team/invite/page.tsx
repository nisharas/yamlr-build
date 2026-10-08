"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function TeamInvitePage() {
    const searchParams = useSearchParams();
    const router = useRouter();

    useEffect(() => {
        const token = searchParams.get("token");
        if (token) window.localStorage.setItem("yamlr_pending_invite", token);
        router.replace("/team");
    }, [router, searchParams]);

    return <main className="mx-auto max-w-2xl px-6 py-24 text-center">
        <h1 className="text-2xl font-semibold">Opening your Yamlr Team invitation…</h1>
    </main>;
}
