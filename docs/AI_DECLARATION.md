# AI / LLM usage declaration (draft)

> Replace the bracketed placeholders before submitting. Keep the statements
> true: if your use differed, edit the text rather than deleting the section.

**Student:** _[Name]_, _[Roll number]_
**Project:** MediCare HMS — Hospital Management System
**Course / institution:** _[Course]_, _[College]_
**Date:** _[Date]_

## 1. Declaration

I declare that I used AI/LLM-based tools during the development of this project
as described below. The tools were used as assistants for drafting, code
generation and review. I reviewed the generated code, ran it locally, tested the
behaviour described in the documentation, and I take responsibility for the
final submitted work.

## 2. Tools used

| Tool | Version / access date | How it was used |
|---|---|---|
| _[e.g. Codebuff / ChatGPT / GitHub Copilot]_ | _[date]_ | _[see below]_ |

## 3. Scope of use

- **Code generation:** drafting Flask blueprints, SQLAlchemy models, WTForms
  classes, Jinja2 templates, CSS and the demo-data script.
- **Refactoring:** simplifying repeated query code and moving business rules
  into the `app/services` layer.
- **Documentation:** drafting the README, report content, API documentation,
  test checklist, viva answers and this declaration. The technical facts were
  checked against the running application.
- **Debugging support:** interpreting error messages (SQLAlchemy
  `IntegrityError`, Jinja2 `UndefinedError`, template `BuildError`) and
  suggesting fixes, which I then applied and verified.

## 4. What was not generated

- No real patient data was generated or used. All demo names, phone numbers and
  clinical notes in `seed_demo.py` are fictional.
- The project does not call any AI/LLM API at runtime, and no AI service is a
  dependency in `requirements.txt`.
- No part of the application sends user or medical data to an external service.

## 5. Verification performed by the student

I confirm that:

1. I read and understand the submitted code.
2. I ran the application locally using SQLite and followed the setup steps in
   `README.md` on a clean machine.
3. I executed the manual test checklist in `docs/TESTING_CHECKLIST.md` and
   observed the documented results _[adjust: list any checks you did not run]_.
4. I can explain the database design, the role-based access rules, the partial
   unique indexes, and the booking/rescheduling logic, as summarised in
   `docs/VIVA.md`.
5. Any screenshots, videos and report content were produced from my own running
   copy of the project.

## 6. Ethical and academic-integrity statement

The use of AI tools was for assistance, not for misrepresenting work. I did not
use AI to fabricate test results, references or data. Where the documentation
states that something was tested, it was tested; where it states that something
was not verified (for example, a formal accessibility audit), it was not
claimed.

## 7. Signature

Signature: ______________________  Date: ______________

---

### Optional appendix — prompt log

If your institution requires a prompt log, list the main requests and what you
did with each answer, for example:

| # | Prompt summary | Outcome |
|---|---|---|
| 1 | "Create a Flask blueprint structure for admin, doctor and patient roles" | Used as a starting point; routes reorganised by hand |
| 2 | "How do I prevent double booking in SQLite with cancelled appointments?" | Implemented the partial unique index idea and wrote the migration check |
| 3 | "Draft a viva answer explaining CSRF" | Edited for accuracy and matched it to the code |
