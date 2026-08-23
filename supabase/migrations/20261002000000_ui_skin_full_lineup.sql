-- The full A/B/C/D lineup for the visual-direction experiment.
--
-- Owner: "i wanted the option to assign a b c or d to a user account to get
-- feedback on what my most active users like." The experiment seeded with
-- Classic + Flat; this brings the other three directions from the review
-- (docs/plans + the direction artifact) in as assignable variants, labeled
-- by their letters so a tester saying "I like C" maps straight onto a row
-- in the admin panel.
--
-- Wholesale replacement of `variants` is safe here because the list is not
-- admin-editable — enabled/rollout/default ARE, and are deliberately not
-- touched. Existing assignments survive: 'flat' keeps its key, and the
-- resolver already treats a pin to a variant that no longer exists as
-- unpinned rather than stranding anyone.
--
-- D ("focus") is honest about its scope: the full One-Thing-at-a-Time from
-- the review is a layout decision; the skin ships its token-level slice
-- (large drill sentence, no elevation) and the label's sublabel says
-- sessions, not the whole app.

-- learner_choice goes OFF: the owner assigns letters ("I as admin choose
-- for the account"), and a tester who could hop between versions
-- mid-trial would be giving feedback about a blur. The Settings section
-- still shows an assigned tester which version they are on, with the
-- feedback box — just no switch. Flip it back on from the admin panel any
-- time an opt-in round is wanted instead.
UPDATE experiments
   SET learner_choice = false,
       variants = '[
         {"key": "classic",   "label": "Classic"},
         {"key": "editorial", "label": "A · Editorial (serif, paper)"},
         {"key": "flat",      "label": "B · Ink Grid (square, no shadows)"},
         {"key": "ground",    "label": "C · Language as Ground (flag-tinted page)"},
         {"key": "focus",     "label": "D · One Thing at a Time (bigger drills)"}
       ]'::jsonb,
       -- One string, two audiences: the admin panel AND an assigned
       -- tester's Settings section both show this, so it explains the
       -- trial, not the admin mechanics.
       description = 'Which look the app is wearing. Classic is what '
         'shipped; A, B, C and D are four visual directions being tried '
         'out. A and B restyle every page; C and D show mostly in study '
         'sessions.',
       updated_at = now()
 WHERE key = 'ui_skin';
