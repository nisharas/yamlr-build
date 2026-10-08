/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
        "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    darkMode: 'class',
    theme: {
        extend: {
            typography: (theme) => ({
                docs: {
                    css: {
                        '--tw-prose-headings': 'hsl(var(--foreground))',
                        '--tw-prose-body': 'hsl(var(--foreground))',
                        '--tw-prose-links': 'hsl(var(--primary))',
                        '--tw-prose-bold': 'hsl(var(--foreground))',
                        '--tw-prose-counters': 'hsl(var(--muted-foreground))',
                        '--tw-prose-bullets': 'hsl(var(--muted-foreground))',
                        '--tw-prose-hr': 'hsl(var(--border))',
                        '--tw-prose-quotes': 'hsl(var(--foreground))',
                        '--tw-prose-quote-borders': 'hsl(var(--primary))',
                        '--tw-prose-captions': 'hsl(var(--muted-foreground))',
                        '--tw-prose-code': 'hsl(var(--foreground))',
                        '--tw-prose-pre-code': 'hsl(var(--foreground))',
                        '--tw-prose-pre-bg': 'hsl(var(--muted))',
                        '--tw-prose-th-borders': 'hsl(var(--border))',
                        '--tw-prose-td-borders': 'hsl(var(--border))',

                        // Base Typography
                        maxWidth: 'none',
                        fontSize: '1rem',
                        lineHeight: '1.75',
                        fontFamily: theme('fontFamily.sans').join(', '),

                        h1: {
                            fontFamily: theme('fontFamily.outfit').join(', '),
                            fontWeight: '800',
                            letterSpacing: '-0.04em',
                            fontSize: '2.25rem',
                            marginBottom: '1.5rem',
                        },
                        h2: {
                            fontFamily: theme('fontFamily.outfit').join(', '),
                            fontWeight: '700',
                            letterSpacing: '-0.02em',
                            fontSize: '1.5rem',
                            marginTop: '2.5rem',
                            marginBottom: '0.75rem',
                            borderBottom: '1px solid hsl(var(--border))',
                            paddingBottom: '0.5rem',
                        },
                        h3: {
                            fontFamily: theme('fontFamily.outfit').join(', '),
                            fontWeight: '700',
                            fontSize: '1.25rem',
                            marginTop: '1.75rem',
                            marginBottom: '0.5rem',
                        },
                        'code::before': { content: '""' },
                        'code::after': { content: '""' },
                        code: {
                            backgroundColor: 'hsl(var(--muted) / 0.5)',
                            padding: '0.2em 0.4em',
                            borderRadius: '0.375rem',
                            fontWeight: '500',
                            fontSize: '0.875em',
                        },
                        pre: {
                            backgroundColor: '#0f172a', // Slate 900
                            border: '1px solid hsl(var(--border) / 0.1)',
                            borderRadius: '1rem',
                            padding: '1.5rem',
                        },
                        blockquote: {
                            fontStyle: 'normal',
                            fontWeight: '400',
                            backgroundColor: 'hsl(var(--muted) / 0.3)',
                            padding: '1rem 1.5rem',
                            borderRadius: '0 1rem 1rem 0',
                            borderLeftWidth: '4px',
                        },
                    },
                },
            }),
            fontFamily: {
                sans: ["var(--font-inter)", "system-ui", "sans-serif"],
                inter: ["var(--font-inter)", "system-ui", "sans-serif"],
                outfit: ["var(--font-outfit)", "system-ui", "sans-serif"],
                heading: ["var(--font-outfit)", "system-ui", "sans-serif"],
                mono: ["var(--font-mono)", "monospace"],
            },
            colors: {
                background: "hsl(var(--background))",
                foreground: "hsl(var(--foreground))",
                primary: {
                    DEFAULT: "hsl(var(--primary))",
                    foreground: "hsl(var(--primary-foreground))",
                },
                secondary: {
                    DEFAULT: "hsl(var(--secondary))",
                    foreground: "hsl(var(--secondary-foreground))",
                },
                muted: {
                    DEFAULT: "hsl(var(--muted))",
                    foreground: "hsl(var(--muted-foreground))",
                },
                accent: {
                    DEFAULT: "hsl(var(--accent))",
                    foreground: "hsl(var(--accent-foreground))",
                },
                destructive: {
                    DEFAULT: "hsl(var(--destructive))",
                    foreground: "hsl(var(--destructive-foreground))",
                },
                border: "hsl(var(--border))",
                input: "hsl(var(--input))",
                ring: "hsl(var(--ring))",
            },
            borderRadius: {
                lg: "var(--radius)",
                md: "calc(var(--radius) - 2px)",
                sm: "calc(var(--radius) - 4px)",
            },
            keyframes: {
                "shimmer": {
                    from: { backgroundPosition: "200% 0" },
                    to: { backgroundPosition: "-200% 0" },
                },
                "shimmer-slide": {
                    "100%": { transform: "translateX(200%)" }
                },
                "shimmer-line": {
                    "0%": { left: "-10%" },
                    "100%": { left: "110%" }
                }
            },
        },
    },
    plugins: [
        require("@tailwindcss/typography"),
    ],
};
