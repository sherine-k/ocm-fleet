import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";

import { parseSysctlValue } from "./keyring-host.mjs";

const REQUIRED_INSTANCES = 1280;
const INSTANCES_SYSCTL = "fs.inotify.max_user_instances";
const PROC_INSTANCES = "/proc/sys/fs/inotify/max_user_instances";

/**
 * CI-only: raise the inotify instance quota shared by rootless Kind nodes.
 * Read the effective kernel value, preserve higher limits, and verify writes;
 * runner-image settings in /etc/sysctl.conf may not have been applied.
 */
export function ensureCiInotifyLimits({
  readFile = (path) => readFileSync(path, "utf8"),
  run = (command, args) => spawnSync(command, args, { encoding: "utf8" }),
  log = console.log,
} = {}) {
  const read = () => parseSysctlValue(readFile(PROC_INSTANCES));
  let current = read();
  if (current < REQUIRED_INSTANCES) {
    const assignment = `${INSTANCES_SYSCTL}=${REQUIRED_INSTANCES}`;
    const result = run("sudo", ["sysctl", "-w", assignment]);
    if (result.status !== 0) {
      throw new Error(
        `failed to configure ${INSTANCES_SYSCTL}: sudo sysctl -w ${assignment} failed${result.stderr ? `\n${result.stderr}` : ""}`,
      );
    }
  }
  current = read();
  if (current < REQUIRED_INSTANCES) {
    throw new Error(
      `failed to configure inotify: ${INSTANCES_SYSCTL} is ${current}, required >= ${REQUIRED_INSTANCES}`,
    );
  }
  log(`inotify: ${INSTANCES_SYSCTL}=${current}`);
}
