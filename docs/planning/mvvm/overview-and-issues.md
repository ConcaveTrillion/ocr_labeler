# MVVM Refactor: Overview and Current Issues

Status: planning reference.

## Overview

This plan describes a refactor to improve separation between Model, ViewModel, View, State, and Operations in OCR Labeler.

## Current Architecture Issues

1. Mixed responsibilities in `models/` (data + presentation concerns)
2. Inconsistent viewmodel organization
3. State vs operations boundaries are blurred
4. Views contain business/navigation logic

## Refactor Goal

Make each layer explicit and easier to evolve:

- Models: pure data/business entities
- ViewModels: presentation and command surface
- Views: UI composition and binding
- State: state storage + notifications
- Operations/Services: business workflows
