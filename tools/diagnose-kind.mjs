import { spawnSync } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";

import { sanitize } from "../e2e/sandbox/run.mjs";

await mkdir("diagnostics", { recursive: true });

async function capture(name, command, args) {
  const result = spawnSync(command, args, {
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
    timeout: 30_000,
  });
  const output = sanitize(
    `${result.stdout ?? ""}\n${result.stderr ?? ""}\n${result.error?.message ?? ""}`,
  );
  await writeFile(`diagnostics/${name}.log`, output);
  console.log(`${name}: exit=${result.status} bytes=${output.length}`);
  if (name === "limits") console.log(output);
  return result.stdout ?? "";
}

await capture("limits", "sysctl", [
  "fs.inotify.max_user_instances",
  "fs.inotify.max_user_watches",
  "kernel.keys.maxkeys",
  "kernel.keys.maxbytes",
]);
await capture("podman-info", "podman", ["info"]);
await capture("podman-ps", "podman", ["ps", "-a"]);
await capture("kernel", "sudo", ["dmesg", "--ctime"]);
await capture("podman-journal", "journalctl", [
  "--user", "-u", "podman.service", "--no-pager",
]);
const containers = await capture("containers", "podman", [
  "ps", "-a", "--format", "{{.ID}} {{.Names}}",
]);
for (const line of containers.trim().split("\n")) {
  const [id, name] = line.split(" ");
  if (!id || !name) continue;
  if (name.startsWith("ocm-fleet-e2e-") || name.startsWith("ocm-fleet--kind-e2e-")) {
    await capture(`${name}-logs`, "podman", ["logs", id]);
    await capture(`${name}-inspect`, "podman", ["inspect", id]);
    if (name.startsWith("ocm-fleet--kind-e2e-")) {
      await capture(`${name}-kubelet`, "podman", [
        "exec", id, "journalctl", "-u", "kubelet", "--no-pager", "-n", "200",
      ]);
    }
  }
}
