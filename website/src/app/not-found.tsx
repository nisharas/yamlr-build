import Link from "next/link";

export default function NotFound() {
    return (
        <div className="min-h-screen bg-white dark:bg-[#0D1117] flex flex-col items-center justify-center px-6 sm:px-8 text-center">
            <div className="max-w-md mx-auto">
                <div className="text-8xl font-extrabold font-outfit tracking-tighter text-slate-200 dark:text-slate-800 mb-4">
                    404
                </div>
                <h1 className="text-2xl font-bold font-outfit text-slate-900 dark:text-white mb-3">
                    Page not found
                </h1>
                <p className="text-slate-600 dark:text-slate-400 mb-8 leading-relaxed">
                    The resource you&apos;re looking for doesn&apos;t exist or has been moved.
                </p>
                <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                    <Link
                        href="/"
                        className="px-6 py-3 min-h-[44px] bg-[#4285F4] hover:bg-[#3367D6] text-white rounded-full font-bold text-sm transition-all active:scale-95 shadow-md shadow-blue-500/20 inline-flex items-center justify-center"
                    >
                        Back to Home
                    </Link>
                    <Link
                        href="/docs"
                        className="px-6 py-3 min-h-[44px] border border-slate-200 dark:border-slate-800 rounded-full text-slate-700 dark:text-slate-300 font-bold text-sm hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-all inline-flex items-center justify-center"
                    >
                        Documentation
                    </Link>
                </div>
                <p className="mt-12 text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-600">
                    Yamlr Manifest Engine
                </p>
            </div>
        </div>
    );
}
