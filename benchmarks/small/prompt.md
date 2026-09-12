# Card effort estimates

Add an optional effort estimate to cards so a team can communicate approximate work size.

A card has no estimate by default. An authorized card editor can set it to exactly one of 1, 2, 3, 5, or 8 points, change it, or clear it from the card detail page. Show a compact labeled estimate on card detail and board card previews when set; omit it when unset. Saving and reloading preserves the value. Invalid values must be rejected without changing the previous estimate. Existing cards and their existing workflows must continue to work. Users without access must not read or modify an estimate through a crafted request. Do not add totals, sorting, filters, notifications, or a new roles system.

Execution contract: Work in the existing Fizzy application and follow its ordinary project style. Implement this feature, add scoped regression tests, and run the checks appropriate to your changes. Preserve existing behavior and account/board authorization. Use locally controlled infrastructure; do not add hosted services. Do not publish, deploy, or push unless the operator separately authorizes it. Ask the operator when blocked; do not silently reduce scope. Report the behavior delivered, tests run, and remaining limitations when ready for review.
