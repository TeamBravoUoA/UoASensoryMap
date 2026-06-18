# Report Drafts

## Project Overview

The UoA Sensory Map is a web application that helps students and visitors choose
campus spaces based on sensory conditions. The system combines a map, a list of
locations, sensory ratings, quiet-zone labels, and later user reports. The core
goal is to make wayfinding more accessible for neurodivergent users and anyone
who benefits from planning around noise, light, smell, temperature, movement,
crowding, and facilities.

## XP Practices

The team will use lightweight Extreme Programming practices during the project:

- Weekly iterations with a Friday demo and retrospective.
- Small tasks tracked as GitHub issues.
- Pairing or mobbing for tricky features.
- Continuous integration through automated checks.
- Test-first or test-soon development for backend behavior.
- Frequent review through pull requests.
- Refactoring in small steps when code becomes hard to understand.

These practices fit the project because the team is small, the deadline is fixed,
and requirements may change after client or supervisor feedback. Short feedback
loops reduce the risk of building features that do not help users.

## Technology Stack

The backend uses Django with Django REST Framework. This gives the team a stable
model layer, admin interface, migration system, and JSON API without needing a
large amount of custom infrastructure.

The frontend uses plain HTML, CSS, and JavaScript. This keeps the project easy to
run locally and avoids a build pipeline. Map and chart libraries can be loaded by
CDN when needed.

SQLite is used for local development because it is simple for every team member
to set up. Deployment can later use environment variables and a production-ready
database if required.

The testing approach uses Django's built-in test framework. API tests verify that
endpoints return the expected data and that filtering behaves correctly.

