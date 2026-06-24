import type { Decision } from "./types";

// The decision triad is the only place colour earns saturation. Each decision
// maps to a spine (the row's left rail), a chip, and a text tone.
export const decisionStyle: Record<
  Decision,
  { spine: string; chip: string; text: string; label: string }
> = {
  APPROVE: {
    spine: "bg-approve",
    chip: "bg-approve/10 text-approve ring-1 ring-inset ring-approve/20",
    text: "text-approve",
    label: "Approve",
  },
  REFER: {
    spine: "bg-refer",
    chip: "bg-refer/10 text-refer ring-1 ring-inset ring-refer/20",
    text: "text-refer",
    label: "Refer",
  },
  REJECT: {
    spine: "bg-reject",
    chip: "bg-reject/10 text-reject ring-1 ring-inset ring-reject/20",
    text: "text-reject",
    label: "Reject",
  },
};
