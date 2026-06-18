# Database Schema

## Current MVP Schema

### Location

Stores each campus location shown on the sensory map.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | Auto ID | Primary key |
| `name` | Text | Location name |
| `description` | Text | Optional summary for users |
| `category` | Choice | `study`, `social`, `quiet`, `food`, `facility`, `other` |
| `latitude` | Float | Map coordinate |
| `longitude` | Float | Map coordinate |
| `auditory` | Integer | 1 low/calm to 5 high/intense |
| `visual` | Integer | 1 low/calm to 5 high/intense |
| `olfactory` | Integer | 1 low/calm to 5 high/intense |
| `thermal` | Integer | 1 low/calm to 5 high/intense |
| `vestibular` | Integer | 1 low/calm to 5 high/intense |
| `is_quiet_zone` | Boolean | Marks low-stimulation spaces |
| `created_at` | Date/time | Created automatically |
| `updated_at` | Date/time | Updated automatically |

## Planned Schema Extensions

### QuietZone

Can be split from `Location.is_quiet_zone` later if the team needs richer quiet
zone details such as opening hours, capacity, access notes, or rules.

### Report

Will store user-submitted condition reports.

| Field | Type | Notes |
| --- | --- | --- |
| `location` | Foreign key | Links to `Location` |
| `comment` | Text | User observation |
| `auditory` | Integer | Optional current rating |
| `visual` | Integer | Optional current rating |
| `olfactory` | Integer | Optional current rating |
| `thermal` | Integer | Optional current rating |
| `vestibular` | Integer | Optional current rating |
| `status` | Choice | `pending`, `approved`, `rejected` |
| `created_at` | Date/time | Created automatically |

### Facility

Will store reusable facility tags for locations.

| Field | Type | Notes |
| --- | --- | --- |
| `name` | Text | Facility label, such as WiFi or power |
| `icon` | Text | Optional icon name |
| `locations` | Many-to-many | Locations that provide this facility |

