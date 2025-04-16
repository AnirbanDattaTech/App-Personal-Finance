# Git Workflow Guide for Personal Expense Tracker

This guide explains how to manage Git history for this project, specifically focusing on:
1. Reverting the project back to a specific milestone (tag).
2. Using branches for developing new features safely.

## 1. Reverting to Milestone `v1.0.0` (Undoing Later Changes)

This process makes your project (local files and GitHub remote) look exactly like it did when tagged `v1.0.0`. It **discards** commits made *after* that tag on the target branch (usually `main`).

**⚠️ WARNING:** This involves rewriting history on the remote repository (`git push --force`). This is dangerous if others are collaborating. Since it's just two users for now, it's manageable, but **proceed with extreme caution** and ensure both users understand the implications before forcing changes to the remote.

### Steps to Revert `main` Branch to `v1.0.0`:

1.  **Confirm Current Branch:** Ensure you're on the branch you intend to reset (e.g., `main`).
    ```bash
    git status
    # Output should indicate you are on branch 'main'
    ```

2.  **Ensure Clean Working Directory:** Commit or stash any changes you want to keep.
    ```bash
    git status
    # Should say "nothing to commit, working tree clean"
    ```

3.  **Reset Local Branch HARD to the Tag:** This moves the local `main` branch pointer back to `v1.0.0` and **discards subsequent commits/changes** on this local branch.
    ```bash
    git reset --hard v1.0.0
    ```

4.  **Force Push to Remote:** Overwrite the remote branch history with your reset local history.
    ```bash
    git push origin main --force
    ```
    *   **🚨 VERY IMPORTANT:** Using `--force` **deletes history** on GitHub for this branch. Only use if absolutely necessary and coordinated.
    *   *(Slightly Safer Alternative):* `git push origin main --force-with-lease` offers a minor safety check against overwriting unseen remote changes, but still force pushes.

**Outcome:** Both your local `main` branch and the `main` branch on GitHub now reflect the exact state of the `v1.0.0` tag. Commits made after `v1.0.0` on this branch are effectively gone from the main history line.

## 2. Using Branches for Development (The Recommended Workflow)

Branches allow you to work on new features (like the Phase 2 chatbot) in isolation without affecting your stable `main` branch.

### Workflow Example (Starting Chatbot Feature after `v1.0.0`):

1.  **Start on `main` and Update:** Ensure your main branch is up-to-date.
    ```bash
    git checkout main
    git pull origin main
    ```

2.  **Create a Feature Branch:** Create and switch to a new branch for the feature.
    ```bash
    git checkout -b feature/chatbot
    # You are now on branch 'feature/chatbot'
    ```
    *   This branch starts as a copy of `main` at this point (`v1.0.0`). Changes here won't affect `main`.

3.  **Develop on the Feature Branch:**
    *   Write code, add files, modify existing ones for the chatbot.
    *   Commit your changes frequently with clear messages:
      ```bash
      # ... make changes ...
      git add .
      git commit -m "Add basic chatbot UI structure"
      # ... make more changes ...
      git add .
      git commit -m "Implement LangGraph agent skeleton"
      ```

4.  **Push the Feature Branch to Remote:** Back up your work and enable potential collaboration.
    ```bash
    # First time pushing this new branch:
    git push -u origin feature/chatbot
    # Subsequent pushes on this branch:
    # git push
    ```

5.  **Continue Development:** Repeat step 3 & 4 as needed. Your `main` branch remains stable.

6.  **Merging (When Feature is Ready & Tested):**
    *   **Switch back to `main`:**
        ```bash
        git checkout main
        ```
    *   **Update `main`:** Ensure `main` has the latest changes from the remote (if any).
        ```bash
        git pull origin main
        ```
    *   **Merge the feature branch into `main`:**
        ```bash
        git merge feature/chatbot
        ```
        *   This brings all the commits from `feature/chatbot` into `main`.
        *   **Handle Conflicts:** If Git reports merge conflicts, you must manually edit the indicated files to resolve the differences, then `git add .` and `git commit` to complete the merge.
    *   **Push the Updated `main`:**
        ```bash
        git push origin main
        ```

7.  **Tag the New Milestone (Optional but Recommended):**
    ```bash
    git tag v2.0.0 -m "Phase 2 complete: Chatbot feature integrated."
    git push origin v2.0.0
    ```

8.  **Clean Up (Optional):** Delete the feature branch after successful merge.
    ```bash
    # Delete local branch
    git branch -d feature/chatbot
    # Delete remote branch
    git push origin --delete feature/chatbot
    ```

### Workflow Summary:

*   **`main`:** Keep stable, reflects working/deployed versions.
*   **Feature Branches:** Create for *all* new work (`git checkout -b <branch_name>`).
*   **Develop:** Code, commit, push on the feature branch.
*   **Merge:** When feature is done, update `main` (`git pull`), then merge the feature branch *into* `main` (`git merge <branch_name>`).
*   **Push `main`**.
*   **Tag** major milestones (`git tag`).

This branching strategy is much safer and is the standard professional practice. Use tags (`v1.0.0`, etc.) to easily revisit specific points in time without disrupting ongoing development.