# Contributing to FTIO
Thank you for considering contributing to FTIO.
 We welcome contributions of all kinds, including bug fixes, new features, documentation improvements, and more.

## Getting Started
> [!note] 
> If you are a student from TU Darmstadt, kindly see these [instructions](/docs/students_contribute.md).

### Step 1: Fork the Repository
1. Visit the [FTIO GitHub repository](https://github.com/tuda-parallel/FTIO).
2. Click the **Fork** button in the top-right corner to create a copy of the repository under your GitHub account.

### Step 2: Clone Your Fork
Clone the forked repository to your local machine:
```bash
git clone https://github.com/<your-username>/FTIO.git
```

Replace `<your-username>` with your GitHub username.

### Step 3: Navigate to the Project Directory
```bash
cd FTIO
```

### Step 4: Build the Project in Debug Mode
Compile the project using the `make debug` command:
```bash
# allows to directly test the changes made
make debug 
```

This will generate a debug build of the project, useful for development and troubleshooting.

### Step 5: Sync with the Original Repository (Optional)
To stay up-to-date with the latest changes from the main repository:
```bash
git remote add upstream https://github.com/tuda-parallel/FTIO.git
git fetch upstream
git merge upstream/main
```

### Step 6: Create an Issue for Your Contribution
Before starting your work, create an issue on the repository to describe the feature, bug fix, or enhancement you plan to implement. This helps us track contributions and avoids duplicate work.

1. Go to the **Issues** tab in the [FTIO repository](https://github.com/tuda-parallel/FTIO).
2. Click **New Issue** and provide a clear title and description.
3. Label the issue appropriately (e.g., `enhancement`, `bug`, or `question`).

### Step 7: Make Your Changes
1. Create a new branch for your changes:
   ```bash
   git checkout -b <your-feature-branch>
   ```
   Replace `<your-feature-branch>` with a descriptive name for your branch.
   
2. Make your desired changes and commit them:
   ```bash
   git add .
   git commit -m "Description of your changes"
   ```

### Step 8: Push Your Changes
Push your changes to your forked repository:
```bash
git push origin <your-feature-branch>
```


### Step 9: Create a Pull Request to the `development` Branch
1. Navigate to the original FTIO repository on GitHub.
2. Click the **Pull Requests** tab, then click **New Pull Request**.
3. Set the target branch to `development`:
   - **Base Repository:** `tuda-parallel/FTIO`
   - **Base Branch:** `development`
   - **Compare Branch:** `<your-feature-branch>`
4. Provide a detailed description of your changes, referencing the issue you created earlier (e.g., `Fixes #123`).
5. Submit your pull request and wait for feedback from the maintainers.

We look forward to your contributions! 🎉

<p align="right"><a href="#ftio">⬆</a></p>


## License

By contributing, you agree that your contributions will be licensed under the same license as this project.

# List Of Contributors

We sincerely thank the following contributors for their valuable contributions:
- [Ahmad Tarraf](https://github.com/a-tarraf)
- [Jean-Baptiste Bensard](https://github.com/besnardjb): Metric proxy integration
- [Anton Holderied](https://github.com/AntonBeasis): bachelor thesis: new periodicity score
- [Amine Aherbil](https://github.com/amineaherbil): master thesis: adaptive change point detection