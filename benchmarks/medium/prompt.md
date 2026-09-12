# Card due dates and overdue filtering

Add optional due dates to help a team find overdue work.

An authorized card editor can set, change, or clear a calendar date from card detail. Store calendar dates, not times. Past dates are allowed; malformed dates are rejected without changing the existing value. Show the date on card detail and board card previews. An open card is overdue exactly when its due date is earlier than today's date in the current viewer's existing configured timezone. A date of today is not overdue; closed cards are never marked overdue. Reopening an overdue card makes it overdue again.

Add an "Overdue" filter to the existing authenticated card filtering experience. It combines with the current board, assignee, and tag selections and retains those selections across pagination and refresh. It must never expose cards outside the viewer's accessible boards/account. Clearing a date immediately removes the card from overdue results. Existing cards remain undated and existing filters continue to work. No reminder email, scheduled job, or external calendar integration is needed.

Execution contract: Work in the existing Fizzy application and follow its ordinary project style. Implement this feature, add scoped regression tests, and run the checks appropriate to your changes. Preserve existing behavior and account/board authorization. Use locally controlled infrastructure; do not add hosted services. Do not publish, deploy, or push unless the operator separately authorizes it. Ask the operator when blocked; do not silently reduce scope. Report the behavior delivered, tests run, and remaining limitations when ready for review.
