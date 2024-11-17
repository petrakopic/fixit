# Fixit 🤖

## About
Fixit was created as a weekend side project sparked by an interesting chat with a colleague. The idea? To automate the 
workflow: issue → AI assistant → code fix → pull request.
The coolest part? I built the core functionality first and let Fixit evolve itself! 🚀
Fixit is a smart, automated bot that listens to your issues, fixes them intelligently, and opens a pull request with the solution.

## Video Walkthrough
[![Fixit Walkthrough](readme_res/video_icon.svg)](https://www.veed.io/view/713d5d2d-016a-48e2-9d8b-f47787edb5ac)


## 📝 **How It Works**

Fixit simplifies the issue resolution process in six easy steps:  

1. **Open an Issue**: Describe the problem or feature request in your repository.  
2. **Tag Fixit**: Add the `@fixit-bot` mention and label the issue with `urgent` (or any label you've configured).  
3. **Wait for Fixit**: The bot picks up the tagged issue for processing.  
4. **Smart Parsing**: Fixit leverages **Claude AI** to break down the issue into clear, actionable tasks.  
5. **Code Fixes with Context**:  
    - Fixit uses **[Aider](https://aider.chat/)**  to generate code changes based on the repository’s context.  
    - Need additional files? Just mention them in the issue, and Fixit will include them.  
6. **Pull Request Creation**:  
    - Fixit opens a PR with the proposed solution.  
    - Tracks how many tokens were used for the process.  
    - Links the issue with the PR, so it closes automatically upon PR approval.  

🛠 **Tip**: Add your coding conventions in the conventions.md file to ensure Fixit adheres to your team's eng guidelines!

---

## 🔗 **Fixit Service Architecture**

<div align="left">
  <img src="readme_res/fixit.png" alt="System Diagram" width="400"/>
</div>


## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

See the [LICENSE](LICENSE) file for details.
