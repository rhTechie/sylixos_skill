---
name: sylixos-network
description: Use when designing, porting, debugging, or validating networking behavior on SylixOS, especially for Linux vs SylixOS network API differences, local-loopback versus physical-port traversal, AF_PACKET behavior, MTU limits, and single-board Ethernet verification without an external peer.
---

# SylixOS Network

Use this skill for general SylixOS networking work.

This skill is intentionally generic. It is for:

- Linux-to-SylixOS networking porting questions
- interpreting surprising board-side network behavior
- choosing a credible network validation method
- understanding raw Ethernet versus local-IP testing

## 1. Separate Validation Goals

Before choosing a test method, distinguish:

1. application/socket connectivity
2. real physical-port traversal
3. throughput or timing-margin stress

Do not use one method to prove all three.

## 2. Local-IP Success Does Not Prove Physical Traversal

If both source and destination IPs belong to the same board:

- `ping`
- `UDP`
- `TCP`

may succeed through host routing or `lo0` instead of traversing the cable.

Reusable rule:

- if the goal is physical-path proof, compare the physical-interface counters and `lo0`

## 3. `SO_BINDTODEVICE` Is Not Sufficient Evidence

Binding to an interface constrains routing, but it does not by itself prove that
traffic to another local IP left the machine.

Treat it as a routing control, not as physical-path evidence.

## 4. When To Use Raw Ethernet

Use raw Ethernet when the board must prove:

- one port transmitted
- another port received
- traffic did not stay in `lo0`

Recommended pattern:

- `AF_PACKET`
- custom EtherType
- explicit source and destination MACs

Evidence hierarchy:

Strong evidence:

- source interface `TX packets` increases
- destination interface `RX packets` increases
- `lo0` does not increase

Weak evidence:

- application receive count alone
- local-IP `ping` success
- local-IP `UDP/TCP` success

## 5. SylixOS `AF_PACKET` Differences From Common Linux Assumptions

Do not assume Linux examples are sufficient unchanged.

Practical requirements on SylixOS include:

- valid `sll_ifindex`
- `sll_hatype = ARPHRD_ETHER`
- Ethernet-capable interface
- interface `UP` and `RUNNING`
- raw frame length within MTU-derived limits

Also remember to include:

- `<net/if_arp.h>`

when using `ARPHRD_ETHER`.

Debug rule:

- treat “send result not equal to requested send length” as failure

## 6. Raw Ethernet and `iperf -u -l 8192` Are Different Workloads

Linux `iperf -u -l 8192` may succeed because UDP/IP can fragment a large
datagram into multiple frames.

Raw Ethernet is different:

- one send corresponds to one L2 frame
- payload must fit the MTU-derived limit unless you implement your own
  fragmentation

Reusable rule:

- never copy a large UDP datagram length directly into a raw single-frame test

## 7. MTU Matters

For raw Ethernet validation:

- inspect MTU explicitly
- compute the allowed raw payload from MTU minus protocol header bytes
- reject oversized payloads with a clear explanation

If larger logical test units are required without jumbo MTU:

- add explicit fragmentation/reassembly in the test protocol

## 8. Throughput Interpretation

If a raw-frame stress test is slower than expected, first decide whether the
bottleneck is:

- packets-per-second
- bandwidth
- user-space validation cost
- syscall overhead
- socket buffering
- MTU/frame-size constraints

Reusable rule:

- separate **PPS-limited** behavior from **bandwidth-limited** behavior before
  judging the link

If observed throughput exceeds negotiated link speed, assume the path is not a
pure physical-path result.

## 9. Packet Counters Are More Reliable Than Byte Counters

On some SylixOS targets:

- packet counters move as expected
- byte counters may be incomplete for some raw-frame paths

Reusable rule:

- prefer `TX/RX packets` as primary evidence
- use `TX/RX bytes` as supporting evidence only

## 10. Generic Single-Board Test Structure

A reusable default structure is:

- phase 1: A -> B
- phase 2: B -> A
- optional phase 3: A <-> B simultaneous

Keep the bidirectional phase optional because it is useful for stress and
full-duplex contention, but it complicates interpretation.

## 11. Reusable Debug Checklist

When network behavior looks wrong on SylixOS, check:

1. Is the destination IP local to the same board?
2. Did `lo0` counters move?
3. Are you trying to prove physical traversal or only socket connectivity?
4. For `AF_PACKET`, did you set `ARPHRD_ETHER`?
5. Is the interface really `UP` and `RUNNING`?
6. Does the requested raw payload exceed the MTU-derived limit?
7. Are you comparing a raw-frame test against a fragmented UDP workload?
8. Are you using interface packet counters, not just user-space receive counts?
