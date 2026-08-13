import { Link } from "react-router-dom"
import { useFetch } from "@/lib/use-fetch"
import { api } from "@/lib/api"

/** Persistent builder credit (project-standards rule 9b, decision 0005
 * section 8): styled like a trailing code comment, consistent with the
 * identity's monospace/technical register rather than a generic "made
 * with love by" footer line. */
export function Footer() {
  const { data } = useFetch(() => api.meta(), [])

  return (
    <footer className="border-t border-border mt-16">
      <div className="mx-auto max-w-7xl px-4 md:px-6 py-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
        <p className="font-mono text-xs text-muted-foreground">
          <span className="text-muted-foreground/60">// </span>
          built by{" "}
          <a
            href={data?.builder_links.github ?? "https://github.com/ethanverper"}
            target="_blank"
            rel="noreferrer"
            className="text-foreground hover:text-signal transition-colors underline underline-offset-4 decoration-muted-foreground/40"
          >
            {data?.builder_name ?? "Ethan Verduzco"}
          </a>
        </p>
        <div className="flex items-center gap-4 font-mono text-xs text-muted-foreground">
          <Link to="/about" className="hover:text-signal transition-colors">
            about / credits
          </Link>
          <a
            href={data?.repo_url ?? "https://github.com/ethanverper/cross-cloud-spend-trace"}
            target="_blank"
            rel="noreferrer"
            className="hover:text-signal transition-colors"
          >
            source
          </a>
          {data?.run_date && <span className="text-muted-foreground/60">pipeline run_date={data.run_date}</span>}
        </div>
      </div>
    </footer>
  )
}
