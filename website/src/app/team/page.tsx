"use client";

import { useCallback, useEffect, useState } from "react";

type Organization = {
    organization_id: string;
    name: string;
    seat_count: number;
    role: "admin" | "member";
    has_seat: number;
};

type TeamDetails = {
    name: string;
    role: "admin" | "member";
    seats: { purchased: number; assigned: number; pending: number; available: number };
    members: Array<{ email: string; role: string; has_seat: number }>;
    invitations: Array<{ email: string; expires_at: number }>;
};

const gateway = process.env.NEXT_PUBLIC_PAYMENT_GATEWAY_URL || "https://gateway.yamlr.dev";

async function api(path: string, init: RequestInit = {}) {
    return fetch(`${gateway}${path}`, {
        ...init,
        credentials: "include",
        headers: { "Content-Type": "application/json", ...init.headers },
    });
}

export default function TeamPage() {
    const [organizations, setOrganizations] = useState<Organization[]>([]);
    const [selectedId, setSelectedId] = useState("");
    const [details, setDetails] = useState<TeamDetails | null>(null);
    const [signedIn, setSignedIn] = useState(false);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");
    const [organizationName, setOrganizationName] = useState("");
    const [inviteEmail, setInviteEmail] = useState("");
    const [seatsToBuy, setSeatsToBuy] = useState(1);

    const loadOrganizations = useCallback(async () => {
        const response = await api("/v1/team/organizations");
        if (response.status === 401) {
            setSignedIn(false);
            return;
        }
        const body = await response.json();
        if (!response.ok) throw new Error(body.error || "Unable to load organizations");
        const rows = body.organizations as Organization[];
        setOrganizations(rows);
        setSignedIn(true);
        const nextId = rows.some((row) => row.organization_id === selectedId) ? selectedId : rows[0]?.organization_id || "";
        setSelectedId(nextId);
    }, [selectedId]);

    const loadDetails = useCallback(async (organizationId: string) => {
        if (!organizationId) {
            setDetails(null);
            return;
        }
        const response = await api(`/v1/team/organizations/${encodeURIComponent(organizationId)}`);
        if (response.status === 404) {
            setDetails(null);
            return;
        }
        const body = await response.json();
        if (!response.ok) throw new Error(body.error || "Unable to load the organization");
        setDetails(body as TeamDetails);
    }, []);

    const refresh = useCallback(async () => {
        try {
            await loadOrganizations();
            if (selectedId) await loadDetails(selectedId);
        } catch (reason) {
            setError(reason instanceof Error ? reason.message : "Unable to load Team details");
        }
    }, [loadDetails, loadOrganizations, selectedId]);

    useEffect(() => { void refresh(); }, [refresh]);

    useEffect(() => {
        const requestedSeats = Number(new URLSearchParams(window.location.search).get("seats"));
        if (Number.isSafeInteger(requestedSeats) && requestedSeats >= 1 && requestedSeats <= 10000) {
            setSeatsToBuy(requestedSeats);
        }
    }, []);

    useEffect(() => {
        if (!signedIn || typeof window === "undefined") return;
        const token = window.localStorage.getItem("yamlr_pending_invite");
        if (!token) return;
        window.localStorage.removeItem("yamlr_pending_invite");
        setBusy(true);
        void api("/v1/team/invitations/accept", { method: "POST", body: JSON.stringify({ token }) })
            .then(async (response) => {
                const body = await response.json();
                if (!response.ok) throw new Error(body.error || "Unable to accept invitation");
                setError("Invitation accepted. Your 24-hour activation token has been sent to your email.");
                await refresh();
            })
            .catch((reason) => setError(reason instanceof Error ? reason.message : "Unable to accept invitation"))
            .finally(() => setBusy(false));
    }, [refresh, signedIn]);

    useEffect(() => {
        if (!selectedId || organizations.find((org) => org.organization_id === selectedId)?.seat_count === 0) {
            setDetails(null);
            return;
        }
        void loadDetails(selectedId).catch((reason) => setError(reason instanceof Error ? reason.message : "Unable to load Team details"));
    }, [loadDetails, organizations, selectedId]);

    const createOrganization = async (event: React.FormEvent) => {
        event.preventDefault();
        setBusy(true);
        setError("");
        try {
            const response = await api("/v1/team/organizations", { method: "POST", body: JSON.stringify({ name: organizationName }) });
            const body = await response.json();
            if (!response.ok) throw new Error(body.error || "Unable to create organization");
            setOrganizationName("");
            await loadOrganizations();
            setSelectedId(body.organization_id);
        } catch (reason) {
            setError(reason instanceof Error ? reason.message : "Unable to create organization");
        } finally { setBusy(false); }
    };

    const buySeats = async (event: React.FormEvent) => {
        event.preventDefault();
        if (!selectedId) return;
        setBusy(true);
        setError("");
        try {
            const response = await api("/v1/payment/checkout", {
                method: "POST",
                body: JSON.stringify({ tier: "team", seats: seatsToBuy, organization_id: selectedId }),
            });
            const body = await response.json();
            if (!response.ok || !body.url) throw new Error(body.error || "Unable to start checkout");
            window.location.assign(body.url);
        } catch (reason) {
            setError(reason instanceof Error ? reason.message : "Unable to start checkout");
        } finally { setBusy(false); }
    };

    const inviteDeveloper = async (event: React.FormEvent) => {
        event.preventDefault();
        if (!selectedId) return;
        setBusy(true);
        setError("");
        try {
            const response = await api(`/v1/team/organizations/${encodeURIComponent(selectedId)}/invitations`, {
                method: "POST", body: JSON.stringify({ email: inviteEmail }),
            });
            const body = await response.json();
            if (!response.ok) throw new Error(body.error || "Unable to send invitation");
            setInviteEmail("");
            await loadDetails(selectedId);
        } catch (reason) {
            setError(reason instanceof Error ? reason.message : "Unable to send invitation");
        } finally { setBusy(false); }
    };

    const updateSeat = async (email: string, assigned: boolean) => {
        if (!selectedId) return;
        const response = await api(`/v1/team/organizations/${encodeURIComponent(selectedId)}/members/seat`, {
            method: "PATCH", body: JSON.stringify({ email, assigned }),
        });
        const body = await response.json();
        if (!response.ok) throw new Error(body.error || "Unable to update seat");
        await loadDetails(selectedId);
    };

    const cancelInvitation = async (email: string) => {
        if (!selectedId) return;
        const response = await api(`/v1/team/organizations/${encodeURIComponent(selectedId)}/invitations`, {
            method: "DELETE", body: JSON.stringify({ email }),
        });
        const body = await response.json();
        if (!response.ok) throw new Error(body.error || "Unable to cancel invitation");
        await loadDetails(selectedId);
    };

    const revokeMember = async (email: string) => {
        if (!selectedId || !window.confirm(`Remove ${email} from this organization? Their offline access can remain valid for up to 24 hours.`)) return;
        const response = await api(`/v1/team/organizations/${encodeURIComponent(selectedId)}/members`, {
            method: "DELETE", body: JSON.stringify({ email }),
        });
        const body = await response.json();
        if (!response.ok) throw new Error(body.error || "Unable to remove member");
        await loadDetails(selectedId);
    };

    const sendActivation = async () => {
        if (!selectedId) return;
        const response = await api(`/v1/team/organizations/${encodeURIComponent(selectedId)}/access-token`, { method: "POST" });
        const body = await response.json();
        if (!response.ok) throw new Error(body.error || "Unable to send activation token");
        setError("A fresh 24-hour activation token has been emailed to your verified account.");
    };

    if (!signedIn) {
        return <main className="mx-auto max-w-3xl px-6 py-24 text-center">
            <h1 className="text-3xl font-bold">Yamlr Team</h1>
            <p className="mt-4 text-slate-600">Sign in with your verified Yamlr account to manage organizations and developer seats.</p>
            <a className="mt-8 inline-flex rounded-full bg-blue-600 px-6 py-3 font-semibold text-white" href={`${gateway}/v1/oidc/login`}>Sign in</a>
        </main>;
    }

    return <main className="mx-auto max-w-5xl space-y-8 px-6 py-20">
        <header>
            <h1 className="text-3xl font-bold">Yamlr Team management</h1>
            <p className="mt-2 text-slate-600">Buy developer seats, invite verified users, and manage assignments.</p>
        </header>
        {error && <p role="status" className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900">{error}</p>}
        <section className="rounded-xl border p-6">
            <h2 className="text-xl font-semibold">Organizations</h2>
            {organizations.length > 0 && <select className="mt-4 w-full rounded border p-3" value={selectedId} onChange={(event) => setSelectedId(event.target.value)}>
                {organizations.map((org) => <option key={org.organization_id} value={org.organization_id}>{org.name} · {org.role}</option>)}
            </select>}
            <form className="mt-5 flex flex-wrap gap-3" onSubmit={createOrganization}>
                <input className="min-w-64 flex-1 rounded border px-3 py-2" value={organizationName} onChange={(event) => setOrganizationName(event.target.value)} placeholder="New organization name" maxLength={100} required />
                <button className="rounded bg-slate-900 px-4 py-2 font-medium text-white" disabled={busy}>Create organization</button>
            </form>
        </section>
        {selectedId && <section className="space-y-6 rounded-xl border p-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div><h2 className="text-xl font-semibold">{details?.name || "Team subscription"}</h2>
                    <p className="mt-1 text-sm text-slate-600">{details ? `${details.seats.assigned} assigned · ${details.seats.pending} invitations · ${details.seats.available} available of ${details.seats.purchased}` : "No active seat pool yet."}</p>
                </div>
                <button className="rounded border px-4 py-2" onClick={() => void sendActivation().catch((reason) => setError(String(reason)))}>Email my activation token</button>
            </div>
            <form className="flex flex-wrap items-end gap-3" onSubmit={buySeats}>
                <label className="text-sm">Developer seats<input className="mt-1 block w-28 rounded border px-3 py-2" type="number" min={1} max={10000} value={seatsToBuy} onChange={(event) => setSeatsToBuy(Math.max(1, Number(event.target.value) || 1))} /></label>
                <button className="rounded bg-blue-600 px-4 py-2 font-medium text-white" disabled={busy}>Buy seats · ${seatsToBuy * 300}/year</button>
            </form>
            {details && <>
                <form className="flex flex-wrap gap-3" onSubmit={inviteDeveloper}>
                    <input className="min-w-64 flex-1 rounded border px-3 py-2" type="email" value={inviteEmail} onChange={(event) => setInviteEmail(event.target.value)} placeholder="developer@example.com" required />
                    <button className="rounded bg-slate-900 px-4 py-2 font-medium text-white" disabled={busy || details.seats.available < 1}>Invite developer</button>
                </form>
                <div className="space-y-3">
                    <h3 className="font-semibold">Members</h3>
                    {details.members.map((member) => <div key={member.email} className="flex flex-wrap items-center justify-between gap-3 border-t pt-3 text-sm">
                        <span>{member.email} · {member.role} · {member.has_seat ? "seat assigned" : "no seat"}</span>
                        <div className="flex gap-2">
                            <button className="rounded border px-3 py-1" onClick={() => void updateSeat(member.email, !member.has_seat).catch((reason) => setError(String(reason)))}>{member.has_seat ? "Release seat" : "Assign seat"}</button>
                            <button className="rounded border border-red-300 px-3 py-1 text-red-700" onClick={() => void revokeMember(member.email).catch((reason) => setError(String(reason)))}>Remove</button>
                        </div>
                    </div>)}
                    {details.invitations.map((invite) => <div key={invite.email} className="flex items-center justify-between gap-3 border-t pt-3 text-sm text-slate-600">
                        <span>Invitation pending · {invite.email}</span>
                        <button className="rounded border px-3 py-1" onClick={() => void cancelInvitation(invite.email).catch((reason) => setError(String(reason)))}>Cancel invite</button>
                    </div>)}
                </div>
            </>}
        </section>}
        <button className="text-sm underline" onClick={() => void api("/v1/auth/logout", { method: "POST" }).then(() => window.location.reload())}>Sign out</button>
    </main>;
}
