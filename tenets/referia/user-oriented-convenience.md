---
id: "user-oriented-convenience"
title: "User-Oriented Convenience"
created: "2025-10-10"
last_updated: "2025-10-10"
version: "1.0"
tags:
- tenet
- user
- convenience
- application
---

# User-Oriented Convenience

## Tenet

**Description**: referia is a user-oriented reviewing tool that provides convenience functionality for ease of use. It should handle implicit behavior explicitly in its own layer, making common tasks easy while maintaining clear separation from the underlying infrastructure. Users should not need to understand implementation details to use the library effectively.

**Quote**: *"Just work, make it easy for humans"*

**Examples**:
- Handle implicit behavior explicitly in referia's own methods
- Provide convenient defaults for common use cases
- Override infrastructure methods to add user-friendly behavior
- Make complex workflows simple through good abstractions
- Hide implementation complexity behind clean APIs

**Counter-examples**:
- Expecting infrastructure to handle implicit behavior
- Making users understand implementation details
- Providing no convenience layer over infrastructure
- Requiring users to know about underlying data flows
- Exposing infrastructure complexity to end users

**Conflicts**:
- **vs Infrastructure Strictness**: When infrastructure needs to be explicit
- Resolution: Handle implicit behavior in referia's layer, keep infrastructure explicit
- **vs Performance**: When convenience adds overhead
- Resolution: Provide both convenient and performant options, document trade-offs
