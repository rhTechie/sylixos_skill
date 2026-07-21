---
name: sylixos-driver-porting
description: Use when porting Linux character-device drivers to SylixOS, especially when adapting character-device registration and interrupt registration/callback logic. Focus on code-level differences between Linux and SylixOS, keep a lightweight process record for non-trivial porting/debugging work, and summarize migration precautions that are reusable across projects.
---

# SylixOS Driver Porting

Use this skill when migrating a Linux driver to SylixOS and the key work involves:

- character-device registration and node creation
- interrupt registration, callback signature adaptation, and interrupt dispatch
- evidence-based porting or debugging that spans multiple edits, builds, uploads, or board-side validation rounds

This skill is intentionally generic. Do not depend on any project-specific path or filename in the final output. Use the current code only to confirm the general rules.

## Scope

Only summarize conclusions that are broadly reusable across projects.

For this skill, the reusable conclusions are limited to:

1. character-device driver registration differences between Linux and SylixOS
2. interrupt registration and interrupt callback differences between Linux and SylixOS

Do not expand into DMA, SDK, samples, build systems, or project-specific debug history unless the user explicitly asks for that.

Process documentation is a workflow requirement, not a third reusable technical category. Keep it during real work, but keep the final reusable summary focused on the two categories above unless the user asks for the investigation history.

## How To Analyze

When using this skill, inspect both Linux and SylixOS branches in the same driver source if available.

Prefer this reference order:

1. native SylixOS BSP drivers in the target platform tree
2. existing Linux-to-SylixOS migrated drivers in the same codebase
3. the original Linux implementation

Do not start from a one-to-one Linux API replacement mindset if the BSP already has an established native SylixOS driver style.

Search patterns:

```sh
rg -n "alloc_chrdev_region|cdev_add|device_create|file_operations|iosDrvInstallEx|iosDevAddEx|FIOSELECT|FIOUNSELECT|request_irq|free_irq|irqreturn_t"
```

Your output should abstract the implementation into OS-level rules, not file-level notes.

## Process Documentation

For non-trivial driver porting or debugging, maintain a process document while working, not only after the final conclusion.

Use an existing project note if one is already present. If not, create a small project-local note such as `docs/sylixos-porting-process.md` when file edits are in scope.

Each major entry should include:

- date to day precision using the actual current date in `YYYY-MM-DD` format
- baseline code version or commit for every touched component
- exact build, upload, module-load, and board-side test commands
- board IP, target path, module or executable path, and result/log file path
- the current hypothesis, the code change made for it, and the expected observation
- whether the result is verified on hardware, compile-only, source-review-only, or still candidate
- rollback note when a change is experimental or only for instrumentation
- write the process document in Chinese by default; keep commands, paths, source identifiers, logs, hashes, and API names unchanged

If the target code directory has no Git history, record that fact and preserve
the files as-is. Do not initialize a local Git repository automatically. Use
patch files or an explicitly authorized repository setup when precise rollback
tracking is needed.

Prefer result files or log files over long live telnet streams. Do not paste raw logs into the final reusable summary; reference the saved paths and extract only the conclusion that matters.

## 1. Character Device Registration

### Linux-side model

The Linux character-device path usually includes:

- allocate major/minor numbers with `alloc_chrdev_region()`
- initialize and attach a cdev with `cdev_init()` and `cdev_add()`
- create a visible device node with `class_create()` and `device_create()`
- implement callbacks through `struct file_operations`
- support readiness notification through `.poll` when needed

Typical Linux callback shape:

```c
static const struct file_operations fops = {
    .open = xxx_open,
    .release = xxx_release,
    .read = xxx_read,
    .unlocked_ioctl = xxx_ioctl,
    .poll = xxx_poll,
};
```

### SylixOS-side model

The SylixOS character-device path is different in two important ways:

- device-driver registration and device-node creation are separated differently from Linux
- `struct file_operations` entries and open-file object semantics differ from Linux

The verified migration pattern is:

- register the driver with `iosDrvInstallEx()`, `iosDrvInstallEx2()`, or wrapper forms such as `API_IosDrvInstallEx2()`
- create the device node with `iosDevAddEx()`
- remove the driver with `iosDrvRemove()`
- use SylixOS `struct file_operations` members such as `fo_create`, `fo_open`, `fo_close`, `fo_read`, `fo_write`, `fo_read_ex`, `fo_write_ex`, `fo_ioctl`

Typical SylixOS callback shape:

```c
static const struct file_operations fops = {
    .fo_create = xxx_open,
    .fo_open = xxx_open,
    .fo_close = xxx_close,
    .fo_read = xxx_read,
    .fo_ioctl = xxx_ioctl,
};
```

### Practical differences to watch

#### 1. Open/close callback prototype is different

Linux `open()` usually receives:

```c
int open(struct inode *inode, struct file *filp)
```

SylixOS `fo_open()` usually receives device-header and open parameters, and often returns a private file handle:

```c
long open(PLW_DEV_HDR pdevhdr, PCHAR pcName, INT iFlags, INT iMode)
```

This means Linux code that stores private state in `filp->private_data` usually needs one extra adaptation step on SylixOS:

- allocate a driver-private file object manually
- store device-private state there
- return that object as the open handle
- free it in `fo_close()`

#### 2. Device-node creation flow is different

In Linux, the node usually appears through `class_create() + device_create()`.

In SylixOS, the migration pattern is usually:

- prepare a `struct device`-like object or device header
- bind driver-private data with `dev_set_drvdata()` or equivalent
- call `iosDevAddEx()` with the final `/dev/...` path

Do not assume that Linux's major/minor management and class model can be reused directly.

Also do not assume every SylixOS char driver still needs a Linux-like `cdev` object.

There are two common migration/implementation styles:

- compatibility-style port:
  - preserve more of the Linux char-device layout
  - keep a Linux-like `struct file_operations`
  - add a SylixOS branch for `fo_*`, `iosDrvInstallEx()`, and `iosDevAddEx()`
- native SylixOS style:
  - skip `alloc_chrdev_region()`, `cdev_init()`, `cdev_add()`, `class_create()`, and `device_create()`
  - directly install a driver number with `iosDrvInstallEx()` or `iosDrvInstallEx2()`
  - directly create `/dev/...` with `iosDevAddEx()`

When reviewing a driver, identify which style it follows before editing it. Mixing the two half-way is a common source of bugs.

#### 3. `poll()` compatibility cannot be copied mechanically

Linux commonly implements readiness notification with:

- `.poll`
- `poll_wait()`
- waitqueue wakeup

SylixOS-side user `poll()` or `select()` support usually requires explicit handling inside `fo_ioctl()`:

- `FIOSELECT`
- `FIOUNSELECT`
- `SEL_WAKE_NODE_ADD`
- `SEL_WAKE_NODE_DELETE`
- `SEL_WAKE_UP` or `SEL_WAKE_UP_ALL`

If the Linux character device exposes blocking readiness semantics, simply porting `read/open/ioctl` is not enough. You must check whether the user side relies on `poll()` or `select()` and then add the SylixOS select-wakeup path explicitly.

In addition, native SylixOS drivers often place select handling inside `fo_ioctl()` rather than as a standalone `.poll` callback. So if Linux code had a separate `.poll`, the port usually requires moving readiness handling into the `FIOSELECT/FIOUNSELECT` branches.

### Character-device migration precautions

When porting Linux char drivers to SylixOS:

1. Do not search for a one-to-one replacement of `alloc_chrdev_region() + cdev_add() + device_create()`. The registration model is different.
2. Re-check every callback prototype in `struct file_operations`; do not assume Linux signatures still apply.
3. If Linux `open()` depends on `inode` or `file`, plan a SylixOS private-handle wrapper for per-open state.
4. If the Linux user API depends on `poll/select`, add `FIOSELECT/FIOUNSELECT` support explicitly; otherwise the device may open successfully but readiness waiting will fail.
5. Separate three concepts during migration:
   - driver registration
   - device-node creation
   - per-open file-instance state
6. Check whether the SylixOS driver should use `fo_read/fo_write` or the extended forms `fo_read_ex/fo_write_ex`; do not collapse positional I/O semantics accidentally.
7. If the target codebase already has native SylixOS char drivers, align to their `iosDrvInstallEx2/API_IosDrvInstallEx2 + iosDevAddEx + fo_*` style instead of forcing a Linux `cdev` mental model into the BSP.
8. If a compatibility-style port and a native SylixOS style are both possible, choose deliberately:
   - use native SylixOS style when long-term maintainability matters more
   - use compatibility-style branching only when you explicitly want to minimize diff against the Linux source

## 2. Interrupt Registration And Callback Adaptation

### Linux-side model

Linux interrupt registration commonly looks like:

```c
request_irq(irq, handler, flags, name, dev_id);
free_irq(irq, dev_id);
```

Typical Linux handler signature:

```c
irqreturn_t handler(int irq, void *dev_id)
```

### SylixOS-side model

SylixOS may still expose `request_irq()` / `free_irq()` style interfaces through a BSP or compatibility layer, but you must not assume the callback signature is identical to Linux.

The verified migration pattern is:

- registration may still be named `request_irq()` / `free_irq()` at the upper layer
- actual handler prototype can change to:

```c
irqreturn_t handler(void *dev_id, ULONG irq)
```

The key point is not the API name. The key point is:

- callback parameter order may change
- IRQ type may change
- any interrupt-dispatch wrapper must invoke the callback with the correct order

In native SylixOS BSP code, another common form is:

```c
irqreturn_t handler(PVOID pvArg, ULONG ulVector)
```

So the portable conclusion is:

- the first parameter is typically the driver-private argument
- the second parameter is typically the vector/irq number
- Linux's `(int irq, void *dev_id)` ordering must not be assumed

### Practical differences to watch

#### 1. `request_irq()` name similarity does not guarantee ABI compatibility

A BSP or compatibility layer may keep the Linux-style registration API name, but the handler typedef may still differ.

Always verify all three together:

1. the handler typedef
2. the actual callback function prototype
3. the place where the dispatcher invokes the callback

If any one of these three still uses Linux assumptions while the others were changed, the interrupt may register successfully but fail at runtime.

#### 2. Dispatcher callback order must match the SylixOS handler typedef

Many drivers do not call the final device handler directly from the top-level OS IRQ entry. Instead they:

- register a shared IRQ dispatcher
- decode status bits
- look up a stored sub-handler
- call the stored sub-handler

During migration, the most dangerous bug is often here:

- Linux dispatcher calls `handler(irq, dev_id)`
- SylixOS path still compiles, but the true callback prototype expects `handler(dev_id, irq)`

So when porting interrupt code, do not stop after adapting the leaf handler prototype. Also inspect every dispatcher or wrapper layer.

This applies not only to PCIe/MSI dispatchers but also to GPIO/irq-server wrappers. Some SylixOS BSP handlers first call an IRQ service helper, then clear or mask the hardware interrupt, and only then schedule deferred work or wake upper layers.

Typical extra steps that may exist in SylixOS BSP interrupt paths:

- call a GPIO or IRQ service helper to confirm the source
- clear the hardware interrupt explicitly
- mask a level-triggered interrupt temporarily
- queue deferred work

So when migrating from Linux, do not assume the interrupt handler body can remain a pure business-logic callback. The BSP may require front-end interrupt housekeeping first.

#### 3. Wakeup behavior tied to interrupts often needs a second SylixOS adaptation

In Linux, an IRQ handler may only need to:

- set a flag
- wake a waitqueue

In SylixOS, if the user layer waits through `select/poll`, the IRQ path often also needs:

- `SEL_WAKE_UP()` or `SEL_WAKE_UP_ALL()`

So the interrupt migration is often coupled with the character-device readiness adaptation.

### Interrupt migration precautions

When porting Linux interrupt code to SylixOS:

1. Do not assume `request_irq()` compatibility means handler compatibility.
2. Check the exact handler prototype expected by the SylixOS BSP or compatibility layer.
3. Check every dispatch wrapper that stores and later calls sub-handlers.
4. Verify callback parameter order explicitly.
5. If the interrupt wakes user-space readers, verify both:
   - kernel-side/blocking wakeup path
   - select/poll wakeup path
6. During bring-up, confirm not only that the IRQ registered successfully, but also that:
   - the interrupt line or source is actually unmasked or enabled
   - the ack/clear path matches the hardware requirement
   - the status bit is decoded correctly
   - the stored handler is found correctly
   - the callback is called with the correct arguments
7. If the interrupt source is GPIO-like or level-triggered, check whether the SylixOS BSP requires explicit source-ack, clear, or mask operations inside the handler before deferring work.
8. When a codebase contains both Linux-compatible and native SylixOS interrupt styles, follow the local typedef and wrapper chain, not the function name alone.

## Output Requirements

When using this skill, summarize only these two categories:

1. character-device registration differences
2. interrupt registration/callback differences

For each category, provide:

- Linux-side pattern
- SylixOS-side pattern
- migration precautions

Do not include project-local paths or filenames in the final reusable summary unless the user explicitly asks for code references.
