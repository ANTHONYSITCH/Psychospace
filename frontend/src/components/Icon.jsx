const paths = {
  overview: <><rect x="3" y="3" width="7" height="7" rx="2" /><rect x="14" y="3" width="7" height="7" rx="2" /><rect x="3" y="14" width="7" height="7" rx="2" /><rect x="14" y="14" width="7" height="7" rx="2" /></>,
  pulse: <path d="M2 12h5l3-7 4 14 3-7h5" />,
  companion: <><path d="M20 11a8 8 0 0 1-8 8H5l-3 3V11a9 9 0 0 1 18 0Z" /><path d="M7 10h0m5 0h0m5 0h0" strokeWidth="3" /></>,
  evolution: <><path d="M3 19h18M5 15l5-5 4 2 6-7M15 5h5v5" /></>,
  memory: <><path d="M4 5h6l2 2 2-2h6v15h-6l-2 2-2-2H4ZM12 7v15" /></>,
  care: <path d="M12 20S3 15 3 8a5 5 0 0 1 9-3 5 5 0 0 1 9 3c0 7-9 12-9 12Z" />,
  moon: <path d="M20 15A9 9 0 0 1 9 3a9 9 0 1 0 11 12Z" />,
  sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1 1m12 12 1 1M5 19l1-1M18 6l1-1" /></>,
  wave: <path d="M2 8c4-7 6 7 10 0s6 7 10 0M2 16c4-7 6 7 10 0s6 7 10 0" />,
  activity: <><path d="m4 18 5-7 4 3 4-8m-5 0h5v5M3 21h18" /></>,
  arrow: <path d="M5 12h14m-5-5 5 5-5 5" />,
  lock: <><rect x="5" y="10" width="14" height="11" rx="3" /><path d="M8 10V7a4 4 0 0 1 8 0v3M12 15v2" /></>,
}
export default function Icon({ name, ...props }) {
  return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name] || paths.overview}</svg>
}
