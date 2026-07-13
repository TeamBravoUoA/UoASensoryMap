# UoA Sensory Map Database Schema

## Core entities

| Entity | Purpose | Key relationships |
| --- | --- | --- |
| `Location` | A campus building or place shown on the map. | Has many `Space`, `LocationFacility`, `LocationSensoryProfile`, `LocationGalleryImage`, and `FeedbackReport` records. |
| `Space` | A specific area within a location, including quiet and sensory spaces. | Belongs to one `Location`; has many `SpaceFacility`, `SpaceSensoryProfile`, and `FeedbackReport` records. |
| `Facility` | A reusable amenity such as Wi-Fi or step-free access. | Linked to locations through `LocationFacility` and spaces through `SpaceFacility`. |
| `SensoryAttribute` | A sensory dimension such as Auditory, Visual, or Crowding. | Linked to location and space ratings through sensory profile records. |
| `FeedbackReport` | A moderated visitor report submitted for one location or one space. | Targets exactly one `Location` or `Space`; starts with `pending` status. |

## Relationship tables

| Entity | Links | Additional data |
| --- | --- | --- |
| `LocationFacility` | `Location` to `Facility` | Availability status and notes. |
| `SpaceFacility` | `Space` to `Facility` | Availability status and notes. |
| `LocationSensoryProfile` | `Location` to `SensoryAttribute` | Rating from 1 to 5 and notes. |
| `SpaceSensoryProfile` | `Space` to `SensoryAttribute` | Rating from 1 to 5 and notes. |
| `LocationGalleryImage` | `Location` to an image | Image file and caption. |

## Integrity rules

- Imported entities use a unique `external_id` for repeatable dataset loading.
- A location-space name pair is unique.
- A facility can be linked to a location or space only once.
- A sensory attribute can be rated only once per location or space.
- Sensory ratings are constrained to values from 1 to 5.
- A feedback report targets one location or one space, never both or neither.
- Quiet zones are represented by `Space.is_quiet_zone`; this avoids duplicating a quiet-space record in a separate table.

## API ownership through Week 6

- Locations are read-only public data and expose nested spaces, quiet zones, facilities, and sensory profiles.
- Reports are submitted through `POST /api/reports/` and are created as `pending` for moderation.
- Location filters support category, sensory axis/rating, quiet-zone status, search, ordering, and available facilities.
