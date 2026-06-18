# Team Charter

## Purpose

Build a sensory-aware campus map for the University of Aberdeen. The app should
help neurodivergent students and visitors find suitable spaces by showing
sensory ratings, quiet zones, facilities, and user feedback.

## Roles

| Member | Lead responsibility | Backup responsibility |
| --- | --- | --- |
| Faizan | Backend, deployment, coordination | Team lead |
| Diana | Security, data, testing | Team co-lead |
| Isa | Frontend | Testing |
| Elorm | Frontend | Documentation, testing |
| Umama | Backend models | Database |
| Ruichi | API design and backend endpoints | Backend models |
| Kristie | Security and testing | Manual testing |

## Meetings And Communication

- Internal team meeting: twice per week.
- Standup: short daily check-in on blockers and progress.
- Supervisor meeting: once per week.
- Client meeting: every two weeks.
- Microsoft Teams or WhatsApp: urgent questions and blockers.
- Outlook: formal updates, agendas, and supervisor communication.
- GitHub: code review, issues, pull requests, and development tracking.

## Working Agreement

- Use one branch per task.
- Open a pull request before merging into `main`.
- Every pull request needs review.
- Ask for help if blocked for more than 30 to 60 minutes.
- A task is done only when code works, tests pass, review is complete, and the
  change is merged.

## Decision Log

| Date | Decision | Reason |
| --- | --- | --- |
| 2026-06-08 | Use Django and Django REST Framework. | The team needs a simple backend with fast API development. |
| 2026-06-08 | Use plain HTML, CSS, and JavaScript. | Avoids a build step and keeps frontend work accessible to the whole team. |
| 2026-06-08 | Use SQLite in development. | Simple local setup for all team members. |
| 2026-06-15 | Expose locations through `/api/locations/`. | Gives the frontend one stable source for map and list data. |

