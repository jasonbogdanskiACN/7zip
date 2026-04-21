<!--
CONTEXT FOR AI ASSISTANTS:
Document Type: Complete reverse engineering guide — Phases 0-7
               C++ codebases + CognitiveIQ MCP tools (GitHub Copilot Chat / Cline / Continue)
               Model: Claude Sonnet 4.5 via CognitiveIQ MCP server (localhost:8000)
Scope: Foundation phases (0-6) that build memory + Phase 7 vertical slice documentation
Last Updated: 2026-02-24

AI DIRECTIVES:
- Complete Section 1 (Session Setup + Fast Path) before doing ANYTHING else
- Read Section 4 (Tool Decision Guide) before touching any code
- Store findings to memory after every phase — Phase 7 depends on this memory
- Run memory_consolidate() after Phase 6 before starting Phase 7
- Run the prose scan at the end of every Phase 7 section
-->

# C++ Reverse Engineering Guide with CognitiveIQ — Phases 0-7

---

## 1. Session Setup + Fast Path

### Every session: connect first

**First time (full indexing, ~1-2 minutes)**:
```
workspace_init(agent_name="Claude", root_dirs=["./src", "./include", "./tests", "./docs"])
```

**Reconnecting after restart (~2 seconds)**:
```
workspace_init(agent_name="Claude", root_dirs=["./src"], skip_indexing=True)
```

If `workspace_init` fails: stop and ask the user to start the server with `uv run -m cognitive_iq`.

### Fast Path decision

After `workspace_init`, run:
```
memory_search("phases foundation [system-name]")
```

- **Memory returns complete Phase 6.3 sign-off** → Skip to Section 12 (Phase 7). Report recalled findings first.
- **Memory returns partial work** → Summarize where work stopped, ask user whether to resume or restart from that phase.
- **No memory found** → Begin at Section 5 (Phase 0).

---

## 2. Documentation Contract

Read this before writing a single word of documentation.

### Allowed in backtick blocks
- File paths and line references: `src/solvers/FoamSolver.cpp:45-78`
- Function signatures: `solve(const Mesh& mesh, const BoundaryConditions& bc)`
- Enum values: `SolverType::IMPLICIT`, `MaterialType::STEEL`
- Mathematical formulas: `σ = F / A`
- Constants with values: `MAX_ITERATIONS = 1000` (source: `config.h`)
- Struct field names when part of a public API: `Result.stress`, `Result.strain`

### Forbidden — rewrite as prose
- C++ function or method bodies of any length
- Pointer operations (`*ptr`, `ptr->field`, `new`, `delete`)
- Template instantiations or template specialization code
- Class or struct definitions and constructor bodies
- Preprocessor macros and `#include` chains
- `std::` algorithm calls written out as code
- Pseudocode that mirrors code structure

### The conversion test
Before writing any ``` block, ask: "Is this a formula, file path, function signature, or enum value?" If no → write a sentence describing **what happens** and **why** instead.

**If a reader could understand the system's behavior from your documentation without looking at the code, you've succeeded. If they still need to read the code to understand what happens, you've transcribed instead of documented.**

---

## 3. NO GUESSING Policy

Applies to every section of every phase, no exceptions.

**CognitiveIQ tools orient you to where answers live. Source code is where you verify them.**

| Forbidden | Required instead |
|-----------|-----------------|
| Guess architecture from a `deep_analyze` summary | Verify in source code or mark `[NEEDS CLARIFICATION]` |
| Assume a formula from `cognitive_next` output | Extract exact formula from source or mark `[NEEDS CLARIFICATION]` |
| Infer a default value or constant | Find its source in config/code or mark `[NOT AVAILABLE]` |
| Make up an error message | Quote it exactly from source or mark `[NEEDS CLARIFICATION]` |
| Assume a state change | Trace the exact field mutation in source or mark `[NEEDS CLARIFICATION]` |

**When in doubt: STOP and ask the user. Never proceed by guessing.**

### Status markers
- `[NEEDS CLARIFICATION]` — information exists but is unclear
- `[NOT AVAILABLE]` — dependency confirmed unavailable
- `[BLOCKED]` — cannot proceed without missing information
- `[VERIFIED: YYYY-MM-DD]` — confirmed with code, data, or domain expert

### Status indicators
✅ Complete | ⚠️ Partial | ❌ Needs Clarification | 🚫 Blocked

---

## 4. Tool Decision Guide

Choose the right tool before touching the codebase. Wrong tool = wasted tokens and slower results.

### Master decision table

| Task | Best Tool | Why not grep |
|------|-----------|-------------|
| Orient to a concept without knowing where it lives | `cognitive_next` | Grep requires exact string; finds by meaning |
| Find all semantic occurrences of a concept | `search` | Grep misses synonyms and related patterns |
| Know exact class/function name, find its definition | `symbol_search` | Matches definitions, not comments or strings |
| Understand architecture of a file or module | `deep_analyze` | Returns structure and intent, not code fragments |
| Understand project directory layout | `navigate` | Returns tree structure; grep returns matching lines |
| Find all classes/structs in the codebase | `kg_list_nodes(type="class")` | Grep for `class ` misses templates, typedefs |
| Trace entity relationships or data flow | `kg_find_path`, `kg_get_neighbors` | Relationships are graph edges, not text patterns |
| Get structured overview of a module | `unified_context` | Returns outlines and schemas; grep returns fragments |
| Inventory public API of a module | `symbols` | Returns structured symbol list, not raw lines |
| Find partial implementations or stubs | Grep (`TODO`, `FIXME`, `stub`) | Exact string match — grep is correct here |
| Know the exact file, need line numbers | Direct file read | Fastest; no semantic overhead needed |
| Search for exact string, constant, or literal | Grep or `symbol_search` | Exact match — no semantic inference needed |
| Understand what state changes during an operation | `cognitive_next` (behavioral query) | Cannot answer "what changes when X happens" |
| Starting any section; check for prior findings | `memory_search` first | Avoids rediscovering known findings |
| First search results include irrelevant content | `cognitive_refine` | Re-running from scratch wastes tokens |
| Need coherent picture across multiple files | `cognitive_synthesize` | Builds unified picture; grep returns fragments |
| Resume prior session context | `memory_search` immediately | Instant recall vs. re-exploring the codebase |

### Progressive narrowing — the default pattern

Apply this sequence for every section:
```
memory_search("[topic] [system-name]")      ← What do we already know?
cognitive_next / unified_context             ← Where does this live? What is it?
search / symbol_search / kg_*               ← Find the specific entity or file
deep_analyze / file read                    ← Verify exact details for documentation
memory_store(content, importance)           ← Preserve before moving on
```

### Memory importance scale

| Importance | Tier | Store when you find... |
|-----------|------|----------------------|
| 0.9 | Semantic | Calculation engine details, state change patterns, dependency access status, readiness assessment |
| 0.8 | Semantic | Entity relationships, external dependencies, constants and unit conversions, project architecture |
| 0.7 | Episodic | Validation rules, service orchestration patterns, implementation gaps |
| 0.6 | Episodic | UI entry points, workflow trigger points, batch behavior |
| 0.5 | Working | Technology stack, directory layout, UI display formats |

---

## 5. Phase 0: Prerequisites & Ground Rules

**Purpose**: Confirm resource access and establish documentation standards before any analysis.

**Deliverable**: `docs/[system-name]/system-analysis/phase-0-prerequisites.md`

```
1. navigate(path="./")
   → Confirm codebase structure (src/, include/, tests/, docs/ exist)

2. navigate or file read for build/config files (CMakeLists.txt, conanfile.txt)
   → Identify external library dependencies declared here

3. Check each required resource: source code, config files, external libraries,
   build environment, domain expert availability, test/sample data

4. memory_store("Phase 0 [system]: resources available=[list], blocked=[list]", importance=0.8)
```

**Document to produce**:

```markdown
## Phase 0: Prerequisites

**Status**: ✅ | ⚠️ | 🚫

| Resource | Status | Location / Notes |
|----------|--------|-----------------|
| Source code | ✅ | [path] |
| Config files | ✅/🚫 | [path or NOT AVAILABLE] |
| External libraries | ✅/🚫 | [path or NOT AVAILABLE] |
| Build environment | ✅/🚫 | [can compile: yes/no] |
| Domain expert | ✅/🚫 | [name or NOT AVAILABLE] |
| Test/sample data | ✅/🚫 | [path or NOT AVAILABLE] |

**NO GUESSING policy**: Confirmed
**Documentation standards**: Confirmed
```

---

## 6. Phase 1: Architecture Analysis

**Purpose**: Understand the project structure, technology stack, design patterns, and high-level data flow.

**Deliverables**: `phase-1-project-structure.md`, `phase-1-technology-stack.md`, `phase-1-architecture-patterns.md`, `phase-1-data-flow.md`

### 1.1 Project Structure + Technology Stack

```
1. navigate(path="./") then navigate(path="./src") and navigate(path="./include")
   → Build the module breakdown — navigate is faster than cognitive_next for structure

2. file read: CMakeLists.txt (or Makefile, vcpkg.json)
   → External dependencies declared here; no semantic search needed

3. memory_store("Project structure [system]: [module list with purpose]", importance=0.5)
   memory_store("Technology stack [system]: C++[ver], [key libs]", importance=0.5)
```

### 1.2 Architectural Patterns

```
1. memory_search("architecture [system-name]")

2. cognitive_next("overall architecture and design patterns in [system-name]")
   → Returns entity IDs, key class names, pattern indicators

3. kg_list_nodes(type="class") → scan names for: Factory, Repository, Service, Manager, Adapter

4. unified_context("architecture layers in [system-name]")
   → Structured outline of layer relationships

5. deep_analyze(path=main_entry_point_file)
   → Understand startup sequence and component initialization

6. memory_store("Architecture patterns [system]: [patterns found]", importance=0.8)
```

### 1.3 Data Flow

```
1. cognitive_next("how data flows through [system-name] from input to output")
   → Identifies the main execution path and transformation points

2. kg_find_path(from=input_entity_id, to=output_entity_id)
   → Traces the concrete path from entry to exit

3. memory_store("Data flow [system]: [entry → layers → exit, key transforms]", importance=0.8)
```

**Phase 1 complete?**
- [ ] Module structure documented with purpose
- [ ] Technology stack listed (C++ version, key libraries)
- [ ] Architectural patterns identified and described in plain English
- [ ] Main data flow traced
- [ ] Findings stored to memory

---

## 7. Phase 2: Data Layer Dissection

**Purpose**: Document all data structures, relationships, persistence patterns, and state changes. Phase 2.5 is a direct dependency of Phase 7 Section 5.

**Deliverables**: `phase-2-entity-model.md`, `phase-2-data-access.md`, `phase-2-5-state-changes.md`

### 2.1 Entity Discovery + Relationships

```
1. memory_search("data structures [system-name]")

2. cognitive_next("main data structures and domain entities in [system-name]")

3. kg_list_nodes(type="class") → filter visually for domain entity names (not services, utilities)

4. symbols(path=data/ or models/ directory)

5. kg_get_neighbors(entity_id) for each major entity
   → Reveals dependencies without manual include tracing

6. file read for exact field names and types
   → Summaries are not precise enough for field documentation

7. memory_store("Domain entities [system]: [entity list with key fields]", importance=0.8)
   memory_store("Entity relationships [system]: [relationship map]", importance=0.8)
```

### 2.2 Data Access Patterns

```
1. cognitive_next("how is data persisted and loaded in [system-name]?")

2. search("database" or "file read" or "serialize" or "persist", collections=["code"])

3. memory_store("Data access [system]: [file-based/DB/in-memory, key classes]", importance=0.7)
```

### 2.5 State Change Patterns ⚠️ CRITICAL — Phase 7 Section 5 depends on this

```
1. memory_search("state changes [system-name]")

2. For each major operation identified in Phase 1.3 data flow:
   cognitive_next("what fields or files change when [operation] executes?")
   → Behavioral semantic query — this is cognitive_next's strongest use case

3. Verify each mutation with file read
   → cognitive_next says WHERE to look; file read confirms WHAT exactly changes

4. cognitive_next("what must succeed together when [operation] runs?")
   → Find RAII guards, transaction objects, rollback logic

5. memory_store("State changes for [operation] in [system]: [field → before/after]", importance=0.9)
   → HIGHEST importance: Phase 7 Section 5 reads this directly
```

**Template for 2.5**:
```markdown
### State Changes: [Operation Name]

| Structure / File | Field / Path | Before | After | Condition |
|-----------------|-------------|--------|-------|-----------|
| [StructName] | [field] | [old value] | [new value] | [always / if X] |
| [output/file.dat] | [exists?] | No | Yes | [always / if X] |

**Transaction boundary**: [Plain English — what must all succeed or all fail together]
**Code Reference**: `path/to/file.cpp:line-range`
```

**Phase 2 complete?**
- [ ] Major domain entities documented with fields and types
- [ ] Entity relationships mapped
- [ ] Data access pattern identified
- [ ] State changes for each major operation documented (2.5)
- [ ] State change findings stored at importance 0.9

---

## 8. Phase 3: Business Logic Analysis

**Purpose**: Document service orchestration, validation rules, and calculation engines. Phase 3.4 is the deepest Phase 7 dependency.

**Deliverables**: `phase-3-service-orchestration.md`, `phase-3-validation-logic.md`, `phase-3-4-calculation-engines.md`

### 3.1 Service Orchestration

```
1. memory_search("services [system-name]")

2. cognitive_next("service layer and business logic orchestration in [system-name]")

3. kg_list_nodes(type="class") → filter for: *Service, *Manager, *Handler, *Orchestrator

4. symbols(path=services/ or business/ directory)

5. memory_store("Services [system]: [service list with purpose]", importance=0.7)
```

### 3.2 Validation Logic

```
1. cognitive_next("input validation and constraint checking in [system-name]")

2. symbol_search(ValidatorClass) if name known from step 1

3. kg_get_neighbors(validator_entity_id) → find all validation dependencies

4. file read for exact error messages and constraint values
   → Must be verbatim; summaries paraphrase

5. memory_store("Validation rules [system]: [rule summary by entity]", importance=0.7)
```

### 3.4 Calculation Engine Analysis ⚠️ MOST CRITICAL — Phase 7 Section 4 depends on this

Never start with grep for a calculation engine.

```
1. memory_search("calculation engine [system-name]")
   → Most likely to have prior findings; check first

2. cognitive_next("calculation engines, solvers, and mathematical processing in [system-name]")
   → PRIMARY tool — returns engine class names, entry points, config sources, entity IDs

3. deep_analyze(path=engine_file_from_step2)
   → Architectural understanding: what it does, what it depends on, how it's structured

4. kg_get_neighbors(engine_entity_id)
   → Find dependencies: lookup tables, constants, external libs, input sources

5. If results include irrelevant code:
   cognitive_refine(positive_ids=[relevant], negative_ids=[irrelevant])

6. If algorithm spans multiple files:
   cognitive_synthesize(doc_ids=[all_relevant_engine_files])

7. file read for exact formula lines
   → For the code reference and to extract the mathematical expression — do not paste C++ code

8. memory_store("Calculation engine [name] in [system]: [algorithm, formulas, entry point]", importance=0.9)
   → HIGHEST importance: Phase 7 Section 4 reads this directly
```

**Template for 3.4**:
```markdown
### Calculation Engine: [Name]

**Type**: [Custom C++ / Third-party static lib / Shared library / External API]
**Location**: `path/to/Engine.cpp` or `libEngine.so`
**Documentation**: ✅ Available at [path] | 🚫 [NOT AVAILABLE]

**Purpose**: [Plain English — what this engine computes]

**Algorithm** (plain English):
1. [Step one — what data is used and what is determined]
2. [Step two — what is computed and from what]

**Mathematical Formulas** [VERIFIED: YYYY-MM-DD]:
`Formula = expression`
Where:
- Variable = [description] ([units], source: [config/lookup/input])
Result units: [units]

**Convergence** (if iterative):
- Stops when: [plain English stopping condition]
- Maximum iterations: [value] (source: [config key / `file.cpp:line`])
- If no convergence: [what the system does]

**Dependencies**:
| Dependency | Type | Access |
|-----------|------|--------|
| [name] | [lookup table / constant / external lib] | ✅ Available / 🚫 Blocked |

**Code Reference**: `path/to/Engine.cpp:line-range`
```

**Phase 3 complete?**
- [ ] Services identified and purpose described
- [ ] Validation rules documented with exact error messages
- [ ] All calculation engines identified (3.4)
- [ ] Formulas extracted with variable definitions and units (or marked `[NEEDS CLARIFICATION]`)
- [ ] Unit conversions and constants documented with sources
- [ ] Calculation engine findings stored at importance 0.9

---

## 9. Phase 4: UI / Client Layer Study

**Purpose**: Document user interaction entry points. Phase 7 Sections 1 and 6 depend on this.

**Deliverables**: `phase-4-client-architecture.md`

```
1. memory_search("UI architecture [system-name]")

2. navigate(path=UI_directory or src/gui/)
   → Structure-first; cheaper than cognitive_next for directory layout

3. cognitive_next("user interface architecture and entry points in [system-name]")
   → Semantic orientation once directories are known

4. symbols(path=main_window_file) → inventory all controls in the primary form

5. For each major workflow, find its UI trigger point:
   symbol_search(ButtonHandlerMethod or CommandClass)
   → This is the file:line that Phase 7 Section 1 needs as "UI Location"

6. memory_store("UI entry points [system]: [workflow → triggering method → file:line]", importance=0.6)
   memory_store("UI architecture [system]: [framework, main screens]", importance=0.6)
```

**Phase 4 complete?**
- [ ] UI framework identified
- [ ] Main screens/dialogs documented with purpose
- [ ] Each major workflow has its UI trigger point (file:line)
- [ ] Findings stored to memory at importance 0.6

---

## 10. Phase 5: Integration Points

**Purpose**: Identify all external systems. Phase 5.3 (Dependency Inventory) is read directly by the Phase 7 prerequisites gate.

**Deliverables**: `phase-5-integration-summary.md`, `phase-5-3-dependency-inventory.md`

### 5.1 External System Discovery

```
1. memory_search("integrations [system-name]")

2. cognitive_next("external systems, APIs, and third-party integrations in [system-name]")

3. search("http", collections=["code"])
   search("socket" or "database" or "file server", collections=["code"])
   → One search per integration category

4. kg_list_nodes → filter for: *Client, *Adapter, *Gateway, *Proxy, *Connector

5. memory_store("External integrations [system]: [list with type and purpose]", importance=0.8)
```

### 5.3 Dependency Inventory ⚠️ CRITICAL — Phase 7 prerequisites gate reads this

For each dependency found in 5.1, determine access status:

```
1. navigate or file read to confirm whether each dependency is present
   → config files, library directories, credential files

2. For lookup tables: file read a sample to confirm structure and access

3. Produce the inventory (template below)

4. memory_store("Dependency inventory [system]: [table summary, blocked items]", importance=0.9)
```

**Template for 5.3**:
```markdown
## Dependency Inventory

### Calculation Engines
| Engine | Type | Location | Documentation | Access |
|--------|------|----------|--------------|--------|
| [name] | [custom/lib/API] | `path/` | ✅/🚫 | ✅ Available / 🚫 Blocked |

### Lookup Tables
| Table / Source | Format | Location | Sample Data | Access |
|----------------|--------|----------|------------|--------|
| [name] | [CSV/binary/DB] | [path] | ✅/🚫 | ✅ Available / 🚫 Blocked |

### Configuration Files
| File | Contains | Access |
|------|----------|--------|
| [filename] | [what it configures] | ✅ Available / 🚫 Blocked |

### Blockers
| Dependency | Workflows Affected | Action Taken | Status |
|-----------|-------------------|-------------|--------|
| [name] | [list] | [access requested from X] | 🚫 Blocked since [date] |
```

**Phase 5 complete?**
- [ ] All external systems identified with integration type
- [ ] Dependency inventory complete (5.3) with access status for every dependency
- [ ] Blockers listed with workflow impact
- [ ] Inventory stored at importance 0.9

---

## 11. Phase 6: Implementation Details & Readiness Assessment

**Purpose**: Document the real state of the implementation, then produce the sign-off that unlocks Phase 7.

**Deliverables**: `phase-6-implementation-details.md`, `phase-6-3-readiness-assessment.md`

### 6.1 Implementation Details

```
1. Grep — correct here because these are exact strings:
   Search for: TODO, FIXME, stub, "not implemented", placeholder

2. search("partial" or "incomplete", collections=["code"])
   → Catch conceptual gaps not marked with TODO

3. file read for each stub found
   → Document what exists vs. what is missing

4. memory_store("Implementation gaps [system]: [list of stubs and partial features]", importance=0.7)
```

### 6.3 Phase 7 Readiness Assessment — Sign-Off Gate

This phase is primarily a memory synthesis, not new codebase exploration.

```
1. Pull all foundation findings from memory:
   memory_search("phases foundation [system-name]")
   memory_search("calculation engine [system-name]")
   memory_search("dependency inventory [system-name]")
   memory_search("state changes [system-name]")

2. cognitive_synthesize(doc_ids=[key docs identified from memory])
   → Build a coherent readiness picture across all phases

3. Classify each workflow as Priority 1 / 2 / 3 based on dependency access

4. memory_store("Phase 6.3 readiness [system]: [overall status, blocked/ready workflows]", importance=0.9)

5. memory_consolidate()
   → Trigger consolidation — Phase 7 can now recall all foundation findings
```

**Template for 6.3**:
```markdown
## Phase 7 Readiness Assessment

**Date**: YYYY-MM-DD
**Overall Status**: ✅ Ready | ⚠️ Partial | 🚫 Blocked

### Readiness Checklist
| Phase | What Was Checked | Status | Notes |
|-------|-----------------|--------|-------|
| 1 | Architecture and data flow | ✅/⚠️/🚫 | |
| 2 | Entities documented | ✅/⚠️/🚫 | |
| 2.5 | State changes captured | ✅/⚠️/🚫 | |
| 3.4 | Calculation engines documented | ✅/⚠️/🚫 | |
| 4 | UI entry points identified | ✅/⚠️/🚫 | |
| 5.3 | Dependency inventory complete | ✅/⚠️/🚫 | |

### Workflow Priority List
| Workflow | Priority | Reason |
|----------|----------|--------|
| [name] | 1 — Ready | All dependencies accessible |
| [name] | 2 — Partial | [specific gap with workaround] |
| [name] | 3 — Blocked | [specific blocker, access requested] |

### Sign-Off
**Decision**: Proceed to Phase 7 | Resolve blockers first | Proceed with partial coverage
```

**Phase 6 complete?**
- [ ] Stubs and partial implementations identified
- [ ] Readiness checklist completed (6.3)
- [ ] Workflow priority list created
- [ ] Sign-off decision recorded
- [ ] Readiness assessment stored at importance 0.9
- [ ] `memory_consolidate()` called

---

## 12. Phase 7: Vertical Slice Template

**Purpose**: Document complete end-to-end user workflows as vertical slices through all layers. Synthesizes everything from Phases 1-6.

**File location**: `docs/[system-name]/vertical-slice-documentation/vertical-slices/phase-7-workflow-[name].md`

**Before starting any workflow, check memory**:
```
memory_search("workflow [workflow-name] [system-name]")
memory_search("calculation engine [system-name]")      ← Section 4 dependency
memory_search("state changes [system-name]")           ← Section 5 dependency
memory_search("dependency inventory [system-name]")    ← Section 3 dependency
```

Begin each workflow document with:
```
# Workflow: [Name]

**Status**: ✅ Complete | ⚠️ Partial | 🚫 Blocked
**Priority**: 1 / 2 / 3
**Last Updated**: YYYY-MM-DD

**Summary**: [One sentence — what the user does and what the system accomplishes]
```

---

### Section 1: Input (Data Entry)

**Purpose**: Document what data the user provides and where each piece comes from.

> ⛔ No code blocks. Describe controls and data sources — not initialization code.

**Information gathering**:
```
memory_search("input fields [workflow-name]")
navigate(path=UI_directory) → orient to UI files
symbols(path=form_file) → inventory controls
deep_analyze(path=form_file) → understand defaults
file read → verify exact default values
memory_store("Input fields [workflow]: [list with sources]", importance=0.6)
```

**Template**:
```
### 1. Input
**UI Location**: [Panel / Dialog] (`path/to/Widget.cpp`)
**Status**: ✅ | ⚠️ | ❌

| Field / Parameter | Control / Input Type | C++ Type | Required | Default | Default Source |
|-------------------|---------------------|----------|----------|---------|----------------|
| [name] | [type] | [double/int/string] | Yes/No | [value] | [config / dict / hardcoded] |

**Code Reference**: `path/to/Widget.cpp:line-range`
```

**Complete?** All defaults verified. ⛔ No code blocks.

---

### Section 2: Validation (Input Verification)

**Purpose**: Document every rule that determines whether input is acceptable.

> ⛔ No code blocks. Describe rules and error messages — not validator method bodies.
> Error messages MUST be quoted verbatim from source — `cognitive_next` paraphrases.

**Information gathering**:
```
memory_search("validation [workflow-name]")
cognitive_next("what validation rules apply to [workflow]?") → orientation + location
kg_get_neighbors(validator_entity_id) → find all validation dependencies
symbol_search(ValidatorClass) → locate specific implementation
file read → exact error messages (verbatim, not from summaries)
memory_store("Validation rules [workflow]: [summary]", importance=0.7)
```

**Template**:
```
### 2. Validation
**Status**: ✅ | ⚠️ | ❌

**Field Rules**:
| Field | Rule | Error / Exception | Enforced At | Code Ref |
|-------|------|-------------------|-------------|----------|
| [name] | [rule] | "[exact quoted message]" | UI/Parser/Solver | `file.cpp:line` |

**Cross-Field Rules**:
- [Plain English: "If [condition], then [parameter] must satisfy [constraint]"]

**Domain / Physical Rules**:
- [Plain English: "The system rejects the operation when [condition] because [reason]"]

**Code Reference**: `path/to/Validator.cpp:line-range`
```

**Complete?** Error messages quoted exactly. ⛔ No code blocks.

---

### Section 3: Preparation (Data Packaging)

**Purpose**: Document how validated input is transformed before the calculation step.

> ⛔ No code blocks. Describe conversions, lookups, and constants — not assembly code.

**Information gathering**:
```
memory_search("unit conversions [system-name]")      ← likely already in memory from Phase 3.4
memory_search("constants [workflow-name]")
search("unit conversion", collections=["code"])       ← if not in memory
symbol_search(ConstantName) → locate specific constant
kg_find_path(from=input_entity, to=calc_entity) → verify data flow
file read → exact constant values and config keys
memory_store("Constants [system]: [list]", importance=0.8)
```

**Template**:
```
### 3. Preparation
**Status**: ✅ | ⚠️ | ❌

**Unit Conversions**:
| From | To | Formula | Code Location |
|------|----|---------|---------------|
| [unit] | [unit] | `formula` | `file.cpp:line` |

**Lookup Tables / Dictionaries**:
| Source | Fields Used | Purpose | Access |
|--------|-------------|---------|--------|
| [name] | [fields] | [what it provides] | ✅ Available / 🚫 Blocked |

**Constants**:
| Name | Value | Units | Source |
|------|-------|-------|--------|
| [name] | [value] | [units] | [header / config key / hardcoded `file.cpp:line`] |

**Data Package**: [Plain English: "The function assembles a [StructName] containing [fields]. [Field] is converted from [unit] to [unit]. Ownership of [resource] is [transferred / shared]."]

**Code Reference**: `path/to/PrepFunction.cpp:line-range`
```

**Complete?** All constants have sources. ⛔ No code blocks.

---

### Section 4: Calculation (Computational Model)

**Purpose**: Document what the system computes, the algorithm, and the mathematical relationships.

> ⛔ No C++ code blocks. Mathematical formulas are the one exception.
> If you have written a ``` block with pointer operations, loops, or conditionals: delete it and rewrite as prose.

**Information gathering** — never start with grep here:
```
memory_search("calculation engine [workflow-name]")   ← likely populated from Phase 3.4
cognitive_next("how does [workflow] compute [output]?") → PRIMARY tool for calculations
deep_analyze(path=calculator_file) → architectural understanding
kg_get_neighbors(engine_entity_id) → find dependencies
cognitive_refine if results include irrelevant code
cognitive_synthesize if algorithm spans multiple files
file read → exact formula lines (for code reference + formula extraction only)
memory_store("Calculation engine [workflow]: [algorithm, key files]", importance=0.9)
```

**Template**:
```
### 4. Calculation
**Status**: ✅ | ⚠️ | 🚫 BLOCKED

**Engine**:
- Type: [Custom C++ / Third-party lib / Shared library / External API]
- Location: `path/to/Solver.cpp` or `libEngine.so`
- Documentation: ✅ Available at [path] | 🚫 [NOT AVAILABLE]

**Algorithm** (plain English):
1. [Step one — what data is used and what is determined]
2. [Step two — what is computed and from what]

**Mathematical Formulas** [VERIFIED: YYYY-MM-DD]:
`Formula = expression`
Where:
- Variable = [description] ([units], source: [config/lookup/input])
Result units: [units]

**Convergence** (if iterative):
- Stops when: [plain English stopping condition]
- Maximum iterations: [value] (source: [config key / `file.cpp:line`])
- If no convergence: [what the system does]

**Parallelism**: [Plain English — e.g., "Domain decomposed into N partitions, solved independently, results gathered after all partitions complete."]

**Code Reference**: `path/to/Solver.cpp:line-range`
```

**Complete?** Algorithm in plain English. Formulas verified. ⛔ No C++ code blocks — only mathematical formulas.

---

### Section 5: Processing (Result Extraction)

**Purpose**: Document what the system does with results — what changes on disk, in memory, or in UI state.

> ⛔ No code blocks. Describe state mutations — not result-processing method bodies.

**Information gathering**:
```
memory_search("state changes [workflow-name]")         ← populated from Phase 2.5
cognitive_next("what changes after [workflow] completes?") → behavioral query
kg_find_path(from=calc_entity, to=output_entity) → trace result flow
symbol_search(ResultWriterClass) → locate output handler
file read → exact field names and output file paths
memory_store("State changes [workflow]: [list]", importance=0.7)
```

**Template**:
```
### 5. Processing
**Status**: ✅ | ⚠️ | ❌

**Output Files Written**:
| File | Format | Location | Contents | Condition |
|------|--------|----------|----------|-----------|
| [filename] | [binary/ASCII/VTK/HDF5] | [path] | [what it holds] | [always / if X] |

**In-Memory State Changes**:
| Structure / Field | Before | After | Condition |
|-------------------|--------|-------|-----------|
| [StructName.field] | [old value] | [new value] | [always / if X] |

**Result Mapping**:
| Calculation Output | Display / Output Field | Conversion Applied |
|-------------------|-----------------------|--------------------|
| [output name] | [field name] | [formula or "none"] |

**Atomicity**: [Plain English — what must all succeed or all fail together]

**Code Reference**: `path/to/ResultWriter.cpp:line-range`
```

**Complete?** All output files and state changes documented. ⛔ No code blocks.

---

### Section 6: Visualization (Output Display)

**Purpose**: Document how results are presented to the user.

> ⛔ No code blocks. Describe what the user sees — not rendering code.
> ASCII screen layout diagrams are acceptable here.

**Information gathering**:
```
memory_search("visualization [workflow-name]")
navigate(path=UI_directory) → orient to display components
symbol_search(DisplayWidgetClass) → locate display class
symbols(path=display_file) → inventory output controls
file read → exact messages, format strings, color values
memory_store("Visualization [workflow]: [summary]", importance=0.5)
```

**Template**:
```
### 6. Visualization
**Status**: ✅ | ⚠️ | ❌

**Display Updates**:
| Control / Viewport / Plot | What It Shows | Format / Units / Color Map |
|--------------------------|--------------|---------------------------|
| [name] | [what it displays] | [format details] |

**User Feedback**:
- On success: [exact message or visual change]
- On failure: [exact message or visual change]

**Export Options**: ✅/❌ CSV | ✅/❌ VTK | ✅/❌ HDF5 | ✅/❌ Image/PDF

**Code Reference**: `path/to/DisplayWidget.cpp:line-range`
```

**Complete?** Messages confirmed from source. ⛔ No code blocks.

---

### Section 7: Iteration (Repeated Execution)

**Purpose**: Document behavior across multiple runs or batch processing.

> ⛔ No code blocks. Describe repeat behavior in plain English.

**Information gathering**:
```
memory_search("batch processing [workflow-name]")
cognitive_next("does [workflow] support batch runs or multiple cases?")
search("parameter sweep" or "multiple runs", collections=["code"])
file read → exact batch size limits and performance constants
memory_store("Iteration [workflow]: [batch support, re-run behavior]", importance=0.6)
```

**Template**:
```
### 7. Iteration
**Status**: ✅ | ⚠️ | ❌

**Batch Processing**: ✅ Supported | ❌ Single run only
[If supported: plain English description of how multiple cases are processed]

**Re-execution Behavior**:
- Previous results are: [overwritten / preserved in timestamped directory / versioned]
- State that persists between runs: [list]
- State that resets on each run: [list]

**Performance**: [Typical wall-clock time for one run; typical batch size and time]

**Code Reference**: [path/to/file.cpp:line-range, if applicable]
```

**Complete?** Re-run behavior verified. ⛔ No code blocks.

---

## 13. Workflow Document Complete?

Before marking a workflow done:
```
memory_search("workflow [workflow-name] complete")
```

If nothing found, run this check:

- [ ] Section 1: All inputs and default sources verified
- [ ] Section 2: All validation rules with exact error messages or exception types
- [ ] Section 3: All conversions, lookups, and constants with sources; ownership described
- [ ] Section 4: Algorithm in plain English; formulas with units; engine verified
- [ ] Section 5: All output files and in-memory state changes documented
- [ ] Section 6: All output displays and user feedback confirmed
- [ ] Section 7: Batch and re-run behavior documented
- [ ] **PROSE SCAN**: Search the document for ``` blocks. Every one must be ONLY a formula, file path, function signature, enum value, or constant. If any contain C++ code logic — rewrite as prose before marking complete.

Then store completion:
```
memory_store("Workflow [name] complete: [one-line summary]", importance=0.8)
memory_consolidate()
```

---

## 14. Prose Conversion Reference

| Instead of pasting... | Write this instead |
|----------------------|-------------------|
| A `for` / range-based `for` loop | "The system processes each [item] in [collection], applying [rule] to each one" |
| A `while` loop | "The system continues [action] until [stopping condition]" |
| An `if/else` block | "If [condition], the system [does A]; otherwise it [does B]" |
| A `try/catch` block | "The operation catches [exception type] and [logs it / reports to user / retries]" |
| Raw pointer ops (`*`, `->`, `new`, `delete`) | "The system [creates / accesses / releases] a [object]. Ownership belongs to [component]" |
| `std::shared_ptr` / `std::unique_ptr` | "The [object] has shared ownership across [A and B]" or "is owned exclusively by [component]" |
| A template instantiation | "The [algorithm / container] is specialized for [type], meaning [behavioral consequence]" |
| A `std::` algorithm call | "The system [sorts / finds / transforms / filters] [collection] by [criterion]" |
| A function or method body | "The function performs [N] steps: [step 1], [step 2], [step 3]. See `file.cpp:45-78`" |
| Struct field assignments | "The [struct] is populated: [field] set to [value], [field] set to [value]" |
| A constructor body | "The component is initialized with [what it needs]; defaults come from [source]" |
| A `switch` statement | "The system selects behavior based on [condition]: when [A] it [does X], when [B] it [does Y]" |
| Virtual method override | "The [derived class] overrides [behavior] so that [what it does differently]" |
| A preprocessor macro | "The macro [NAME] [controls / expands to] [plain English description]" |
| Callback / function pointer setup | "When [event occurs], the system invokes [callback] to [what happens]" |
| RAII / scope guard | "The [resource] is automatically released when [scope] exits, regardless of success or failure" |

---

## 15. Folder Structure

```
docs/[system-name]/
├── system-analysis/                        ← Phases 0-6
│   ├── phase-0-prerequisites.md
│   ├── phase-1-project-structure.md
│   ├── phase-1-technology-stack.md
│   ├── phase-1-architecture-patterns.md
│   ├── phase-1-data-flow.md
│   ├── phase-2-entity-model.md
│   ├── phase-2-data-access.md
│   ├── phase-2-5-state-changes.md          ← Phase 7 Section 5 dependency
│   ├── phase-3-service-orchestration.md
│   ├── phase-3-validation-logic.md
│   ├── phase-3-4-calculation-engines.md    ← Phase 7 Section 4 dependency
│   ├── phase-4-client-architecture.md
│   ├── phase-5-integration-summary.md
│   ├── phase-5-3-dependency-inventory.md   ← Phase 7 prerequisites dependency
│   ├── phase-6-implementation-details.md
│   └── phase-6-3-readiness-assessment.md  ← Phase 7 sign-off gate
└── vertical-slice-documentation/           ← Phase 7
    ├── phase-7-summary.md
    ├── phase-7-prerequisites-complete.md
    ├── phase-7-priority-1-index.md
    └── vertical-slices/
        ├── phase-7-workflow-[name1].md
        └── phase-7-workflow-[name2].md
```

---

*Last Updated: 2026-02-24*
*Model: Claude Sonnet 4.5 via CognitiveIQ MCP (localhost:8000)*
