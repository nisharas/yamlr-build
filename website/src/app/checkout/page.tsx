"use client";

import React, { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Navigation from "@/components/Navigation";
import Footer from "@/components/Footer";
import { RevealAnimation } from "@/components/Hero";
import { CreditCard, ShieldCheck, Zap, Loader2 } from "lucide-react";

function CheckoutContent() {
    const searchParams = useSearchParams();
    const requestedTier = searchParams.get("tier") || "team";
    const tier = requestedTier.toLowerCase() === "pro" ? "team" : requestedTier.toLowerCase();
    const [seats, setSeats] = useState(1);
    const [loading, setLoading] = useState(false);

    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    const isEnterprise = tier.toLowerCase() === "enterprise";
    const isIndividual = tier === "free" || tier === "individual";
    const planTitle = isEnterprise ? "Yamlr Enterprise" : "Yamlr Team Annual";
    const priceDisplay = isEnterprise ? "Contact Sales" : isIndividual ? "$0" : `$${300 * seats}`;
    const priceSubtext = isEnterprise
        ? "Sales-led organization grant with contracted seats or nodes"
        : isIndividual
            ? "Free forever"
            : "Billed annually at $25/developer/month ($300 per developer/year)";

    const handlePayment = async () => {
        if (isEnterprise || isIndividual) return;
        setLoading(true);
        setErrorMessage(null);
        window.location.href = `/team?seats=${seats}`;
    };

    return (
        <div className="max-w-xl w-full space-y-10">
            <RevealAnimation>
                <div className="text-center space-y-4">
                    <h1 className="text-3xl sm:text-4xl md:text-5xl font-extrabold font-outfit tracking-tight text-slate-950 dark:text-white">
                        {isEnterprise ? "Talk to sales about " : isIndividual ? "Yamlr " : "Complete your "}
                        <span className="text-[#4285F4]">{isEnterprise ? "ENTERPRISE" : isIndividual ? "INDIVIDUAL" : "TEAM"}</span>
                        {!isEnterprise && !isIndividual ? " upgrade." : ""}
                    </h1>
                    <p className="text-slate-600 dark:text-slate-400 text-base sm:text-lg font-medium">
                        {isEnterprise
                            ? "Enterprise is a sales-led organization grant with contracted seats or nodes and offline activation."
                            : isIndividual
                                ? "Individual includes free scanning and healing. No purchase or license activation is required."
                                : "Each paid seat belongs to a named developer and can be used across that developer's devices."}
                    </p>
                </div>
            </RevealAnimation>

            <RevealAnimation delay={100}>
                <div className="bg-slate-50 dark:bg-[#161B22] border border-slate-200 dark:border-slate-800 rounded-2xl p-8 space-y-8 shadow-xl">
                    <div className="space-y-4">
                        <div className="flex justify-between items-center text-xs font-bold uppercase tracking-widest text-slate-400">
                            <span>Subscription</span>
                            <span>Price</span>
                        </div>
                        <div className="flex justify-between items-end">
                            <div className="space-y-1">
                                <h2 className="text-xl font-bold font-outfit text-slate-900 dark:text-white">{planTitle}</h2>
                                <p className="text-xs text-slate-500">{priceSubtext}</p>
                            </div>
                            <div className="text-right">
                                <span className="text-3xl font-black text-slate-900 dark:text-white">{priceDisplay}</span>
                                {!isEnterprise && <span className="text-xs text-slate-500 block">{isIndividual ? "/ forever" : "/ year"}</span>}
                            </div>
                        </div>
                    </div>

                    {!isEnterprise && !isIndividual && (
                        <label className="flex items-center justify-between gap-4 text-sm text-slate-600 dark:text-slate-300">
                            <span>Developer seats</span>
                            <input
                                type="number"
                                min={1}
                                max={1000}
                                value={seats}
                                onChange={(event) => setSeats(Math.max(1, Math.min(1000, Number(event.target.value) || 1)))}
                                className="w-24 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-right"
                            />
                        </label>
                    )}

                    <hr className="border-slate-200 dark:border-slate-800" />

                    <div className="space-y-4">
                        <div className="flex items-center gap-4 text-sm text-slate-600 dark:text-slate-300">
                            <div className="w-8 h-8 rounded-full bg-emerald-500/10 flex items-center justify-center text-emerald-500 shrink-0">
                                <ShieldCheck size={18} />
                            </div>
                            <span>{isEnterprise ? "Offline organization grant" : isIndividual ? "Free plan" : "Named developer seats"}</span>
                        </div>
                        <div className="flex items-center gap-4 text-sm text-slate-600 dark:text-slate-300">
                            <div className="w-8 h-8 rounded-full bg-blue-500/10 flex items-center justify-center text-[#4285F4] shrink-0">
                                <Zap size={18} />
                            </div>
                            <span>{isEnterprise ? "Contracted entitlements managed by your organization administrator." : isIndividual ? "Core scanning and free healing are included." : "Team features follow the named developer across devices."}</span>
                        </div>
                    </div>

                    {errorMessage && (
                        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 text-xs text-amber-600 dark:text-amber-400 space-y-2">
                            <p className="font-bold">{errorMessage}</p>
                            <p className="text-[11px] text-slate-500">Contact sales for payment and activation support.</p>
                            <p className="text-[11px] pt-1">
                                Need an invoice or purchase order?{" "}
                                <a href="mailto:sales@yamlr.dev" className="text-[#4285F4] underline font-semibold">Contact Sales directly</a>.
                            </p>
                        </div>
                    )}

                    {isEnterprise ? (
                        <a href="mailto:sales@yamlr.dev?subject=Yamlr%20Enterprise%20Licensing" className="w-full inline-flex items-center justify-center gap-2 min-h-[48px] py-3.5 px-6 rounded-full bg-[#059669] hover:bg-emerald-700 text-white text-sm font-bold tracking-normal shadow-md transition-all">
                            Contact Enterprise Sales
                        </a>
                    ) : isIndividual ? (
                        <a href="/#install" className="w-full inline-flex items-center justify-center gap-2 min-h-[48px] py-3.5 px-6 rounded-full bg-[#4285F4] hover:bg-[#3367D6] text-white text-sm font-bold tracking-normal shadow-md transition-all">
                            Install Yamlr
                        </a>
                    ) : (
                        <button
                            onClick={handlePayment}
                            disabled={loading}
                            className="w-full inline-flex items-center justify-center gap-2 min-h-[48px] py-3.5 px-6 rounded-full bg-[#4285F4] hover:bg-[#3367D6] text-white text-sm font-bold tracking-normal shadow-md shadow-blue-500/20 disabled:opacity-50 transition-all"
                        >
                            {loading ? <Loader2 className="animate-spin" size={20} /> : <>Proceed to Secure Payment <CreditCard size={18} /></>}
                        </button>
                    )}

                    <p className="text-center text-xs font-medium text-slate-500 dark:text-slate-400">
                        {isEnterprise ? "Offline grants for contracted Enterprise customers" : "Runs locally · No license needed for Individual"}
                    </p>
                </div>
            </RevealAnimation>
        </div>
    );
}

export default function CheckoutPage() {
    return (
        <div className="min-h-screen bg-white dark:bg-[#0D1117] flex flex-col">
            <Navigation />

            <main className="flex-1 flex flex-col items-center justify-center pt-24 sm:pt-28 pb-20 px-6 sm:px-8">
                <Suspense fallback={<div className="py-20 text-slate-400 font-mono text-sm">Loading checkout...</div>}>
                    <CheckoutContent />
                </Suspense>
            </main>

            <Footer />
        </div>
    );
}
