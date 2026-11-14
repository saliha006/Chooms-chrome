"""The lerobot-train command line for one run (LeRobot 0.7). Pure, so it is testable without Modal."""

SWEEP_EPISODES = (18, 36, 54)  # F11: success vs number of demonstrations (decisions.md D9)


def job_name(policy: str, episodes: int, steps: int) -> str:
    return f"{policy}-{episodes or 'all'}ep-{steps}st"


def build(policy: str, dataset: str, steps: int, lr: float, output_dir: str, episodes: int = 0, batch_size: int = 8) -> list[str]:
    if policy not in ("act", "smolvla"):
        raise ValueError(f"policy must be act or smolvla, got {policy}")
    cmd = [
        "lerobot-train",
        "--policy.type=act" if policy == "act" else "--policy.path=lerobot/smolvla_base",
        f"--dataset.repo_id={dataset}",
        f"--steps={steps}",
        f"--batch_size={batch_size}",
        f"--policy.optimizer_lr={lr}",  # 1e-5 for ACT: 1e-4 makes it output one pose whatever it sees (Studio #998)
        "--policy.device=cuda",
        "--policy.push_to_hub=false",
        "--wandb.enable=false",
        f"--output_dir={output_dir}",
        f"--job_name={job_name(policy, episodes, steps)}",
    ]
    if episodes:
        cmd.append(f"--dataset.episodes=[{','.join(str(i) for i in range(episodes))}]")
    return cmd
