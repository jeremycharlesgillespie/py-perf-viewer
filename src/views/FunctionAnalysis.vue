<template>
  <div class="container mt-4">
    <h1 class="mb-4">Function Analysis: {{ functionName }}</h1>
    
    <div class="alert alert-info">
      <i class="fas fa-info-circle"></i>
      Function Analysis view will be implemented in the next phase.
      <router-link to="/" class="btn btn-primary ms-3">
        Back to Dashboard
      </router-link>
    </div>
  </div>
</template>

<script>
export default {
  name: 'FunctionAnalysis',
  props: {
    functionName: {
      type: String,
      required: true
    }
  }
}
</script>