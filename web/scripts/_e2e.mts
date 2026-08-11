import { startRender, getJob, ROOT } from "../lib/sandbox";

async function main() {
  console.log("ROOT =", ROOT);
  const job = await startRender({ slug: "why-is-the-sky-blue", title: "Why Is the Sky BLUE?" });
  console.log("job:", job.id);

  const deadline = Date.now() + 22 * 60_000;
  let lastLen = 0;
  while (Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, 15_000));
    const v = await getJob(job.id);
    if (v.log.length > lastLen) {
      process.stdout.write(v.log.slice(lastLen));
      lastLen = v.log.length;
    }
    if (v.status === "done" || v.status === "failed") {
      console.log(`\n=== ${v.status.toUpperCase()} exit=${v.exitCode} ===`);
      console.log("artifacts:", v.artifacts.join(", ") || "(none)");
      if (v.qc) console.log(v.qc.split("\n").slice(0, 16).join("\n"));
      console.log("\nJOB_ID=" + job.id);
      return;
    }
  }
  console.log("timed out; JOB_ID=" + job.id);
}
main().catch((e) => { console.error(e); process.exit(1); });
