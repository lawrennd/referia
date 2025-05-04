# Code Improvement Proposals (CIPs)

## Overview
Code Improvement Proposals (CIPs) are documents that describe proposed changes to the referia codebase. They serve as a way to document design decisions, track progress on implementation, and provide context for code changes.

## Process

1. **Create a New CIP**:
   - Copy the `cip_template.md` file
   - Name it `cipXXXX.md` where XXXX is the next number in sequence
   - Fill in the details of your proposal

2. **Review**:
   - Share the CIP with other developers for feedback
   - Update the CIP based on feedback

3. **Implementation**:
   - Update the CIP with implementation details
   - Mark tasks as complete in the Implementation Status section as you make progress

4. **Completion**:
   - Once all tasks are complete, mark the CIP as completed
   - Add a summary of the changes made

## CIP Status

Each CIP can have one of the following statuses:

- **Draft**: Initial proposal, subject to change
- **Accepted**: Proposal has been accepted and is ready for implementation
- **In Progress**: Implementation is underway
- **Completed**: Implementation is complete
- **Rejected**: Proposal has been rejected

## Git Branching Protocol

To maintain a clean commit history and allow for proper code review, we follow this git branching protocol for CIPs:

1. **Main Branch**: 
   - Contains the CIP infrastructure (README.md, cip_template.md)
   - Merged and completed CIPs

2. **Feature Branches**:
   - Create a branch named `cip-XXXX` for each CIP (e.g., `cip-0001`)
   - Implement the changes described in the CIP on this branch
   - Include both the CIP document and the code changes in the branch

3. **Pull Request Process**:
   - Once implementation is complete, create a PR from your feature branch to main
   - Add appropriate reviewers
   - Only merge once approved and all CI checks pass

This approach keeps the main branch clean while allowing for detailed discussion and implementation of each individual CIP.

## Current CIPs

- [CIP-0002](./cip0002.md): Refactoring Compute Class Inheritance Structure
- [CIP-0001](./cip0001.md): Standardization of Test Methods for Compute Class

## Creating a Good CIP

A good CIP should:

1. Clearly state the problem being solved
2. Explain the proposed solution in detail
3. Consider alternative approaches
4. Address backward compatibility
5. Include a testing strategy
6. Provide a clear implementation plan
7. Consider potential drawbacks or risks 
