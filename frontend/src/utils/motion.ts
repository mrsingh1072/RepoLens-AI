import type { Transition, Variants } from "framer-motion";

/**
 * STRATA motion language — "Settle".
 * Everything moves like a mass coming to rest: springs only,
 * fast start, soft landing, at most one gentle overshoot.
 */

/** Buttons, toggles, chips — immediate response. */
export const snap: Transition = { type: "spring", stiffness: 520, damping: 32, mass: 0.6 };

/** Cards, list items, panels — the default. */
export const settle: Transition = { type: "spring", stiffness: 380, damping: 30, mass: 0.8 };

/** Page transitions and large surfaces — unhurried. */
export const drift: Transition = { type: "spring", stiffness: 200, damping: 26, mass: 1 };

export const fadeInUp: Variants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: settle },
};

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: 0.3 } },
};

export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.98 },
  show: { opacity: 1, scale: 1, transition: settle },
};

/** Container that staggers its children on mount (capped for calm). */
export const staggerContainer = (stagger = 0.04, delay = 0): Variants => ({
  hidden: {},
  show: { transition: { staggerChildren: stagger, delayChildren: delay } },
});

/** Old page settles down 6px; new page rises 10px. ~200ms felt time. */
export const pageTransition: Variants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: drift },
  exit: { opacity: 0, y: -6, transition: { duration: 0.15, ease: "easeIn" } },
};
